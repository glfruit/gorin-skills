import {
  lstat,
  mkdir,
  readFile,
  readdir,
  rename,
  rm,
  writeFile,
} from "node:fs/promises";
import { dirname, join, relative } from "node:path";
import { parse } from "yaml";
import {
  buildCatalog,
  buildSkillPackages,
  loadExternalSources,
  renderDocumentationIndex,
  resolveProfile,
  validateRepository,
  validateLifecycleTransitions,
} from "./governance.mjs";

const BUMP_ORDER = { patch: 1, minor: 2, major: 3 };

async function exists(path) {
  try {
    await lstat(path);
    return true;
  } catch (error) {
    if (error.code === "ENOENT") return false;
    throw error;
  }
}

function assertBump(value) {
  if (!BUMP_ORDER[value]) {
    throw new Error(`unsupported semantic increment ${value ?? "(missing)"}`);
  }
  return value;
}

function highestBump(left, right) {
  if (!left) return right;
  return BUMP_ORDER[right] > BUMP_ORDER[left] ? right : left;
}

function bumpVersion(version, bump) {
  const match = version.match(/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+].*)?$/);
  if (!match) throw new Error(`cannot bump invalid semantic version ${version}`);
  let major = Number(match[1]);
  let minor = Number(match[2]);
  let patch = Number(match[3]);
  if (bump === "major") {
    major += 1;
    minor = 0;
    patch = 0;
  } else if (bump === "minor") {
    minor += 1;
    patch = 0;
  } else {
    patch += 1;
  }
  return `${major}.${minor}.${patch}`;
}

async function listYamlFiles(path) {
  try {
    return (await readdir(path, { withFileTypes: true }))
      .filter((entry) => entry.isFile() && entry.name.endsWith(".yaml"))
      .map((entry) => entry.name)
      .sort();
  } catch (error) {
    if (error.code === "ENOENT") return [];
    throw error;
  }
}

export async function computeReleasePlan(root) {
  const skills = await validateRepository(root);
  const externalSources = await loadExternalSources(root);
  const repositoryPath = join(root, "release", "repository.yaml");
  let repository;
  try {
    repository = parse(await readFile(repositoryPath, "utf8"));
  } catch (error) {
    if (error.code === "ENOENT") {
      throw new Error("Missing release/repository.yaml");
    }
    throw error;
  }
  if (repository?.schema_version !== 1 || !repository.version) {
    throw new Error("Invalid release/repository.yaml");
  }
  const lifecycleBaselinePath = join(
    root,
    "release",
    "baselines",
    `catalog-${repository.version}.json`,
  );
  try {
    const lifecycleBaseline = JSON.parse(
      await readFile(lifecycleBaselinePath, "utf8"),
    );
    validateLifecycleTransitions(skills, lifecycleBaseline);
  } catch (error) {
    if (error.code === "ENOENT") {
      throw new Error(
        `Missing lifecycle baseline ${lifecycleBaselinePath}`,
      );
    }
    throw error;
  }

  const fragmentsRoot = join(root, "release", "fragments");
  const fragmentNames = await listYamlFiles(fragmentsRoot);
  if (fragmentNames.length === 0) throw new Error("No release fragments");

  const skillsById = new Map(skills.map((skill) => [skill.skillName, skill]));
  const skillBumps = new Map();
  const fragments = [];
  let repositoryBump;
  for (const name of fragmentNames) {
    const path = join(fragmentsRoot, name);
    const source = await readFile(path, "utf8");
    const fragment = parse(source);
    if (fragment?.schema_version !== 1) {
      throw new Error(`${name}: release fragment schema_version must be 1`);
    }
    if (typeof fragment.summary !== "string" || !fragment.summary.trim()) {
      throw new Error(`${name}: release fragment summary must be non-empty`);
    }
    const fragmentRepositoryBump = assertBump(fragment.repository);
    repositoryBump = highestBump(repositoryBump, fragmentRepositoryBump);
    for (const [skillName, bumpValue] of Object.entries(fragment.skills ?? {})) {
      if (!skillsById.has(skillName)) {
        throw new Error(`${name}: unknown skill ${skillName}`);
      }
      const bump = assertBump(bumpValue);
      skillBumps.set(skillName, highestBump(skillBumps.get(skillName), bump));
    }
    fragments.push({ name, path, source, summary: fragment.summary.trim() });
  }

  const skillChanges = [...skillBumps.entries()]
    .map(([id, bump]) => {
      const from = skillsById.get(id).manifest.version;
      return { id, from, to: bumpVersion(from, bump), bump };
    })
    .sort((left, right) => left.id.localeCompare(right.id));
  const repositoryChange = {
    from: repository.version,
    to: bumpVersion(repository.version, repositoryBump),
    bump: repositoryBump,
  };
  const plan = {
    schema_version: 1,
    fragments: fragments.map((fragment) => fragment.name),
    repository: repositoryChange,
    skills: skillChanges,
    artifacts: [
      "CHANGELOG.md",
      "catalog/index.json",
      "docs/skills/index.md",
      "release/packages/",
      "release/profiles/",
      "release/baselines/",
      "release/repository.yaml",
    ],
  };

  return {
    plan,
    context: {
      skills,
      externalSources,
      fragments,
      repositoryPath,
      lifecycleBaselinePath,
    },
  };
}

function withVersion(skill, versionById) {
  const version = versionById.get(skill.skillName);
  if (!version) return skill;
  return { ...skill, manifest: { ...skill.manifest, version } };
}

function renderChangelog(previous, plan, fragments) {
  const summaries = fragments.map((fragment) => `- ${fragment.summary}`).join("\n");
  const changes = plan.skills
    .map((skill) => `- \`${skill.id}\`: ${skill.from} → ${skill.to} (${skill.bump})`)
    .join("\n");
  const section = [
    `## ${plan.repository.to}`,
    "",
    summaries,
    ...(changes ? ["", changes] : []),
    "",
  ].join("\n");
  const normalized = previous?.trim()
    ? previous.trimEnd()
    : "# Changelog";
  if (normalized.startsWith("# Changelog")) {
    const rest = normalized.slice("# Changelog".length).trimStart();
    return `# Changelog\n\n${section}${rest ? `${rest}\n` : ""}`;
  }
  return `# Changelog\n\n${section}${normalized}\n`;
}

async function stageRelease(root, computed) {
  const { plan, context } = computed;
  const stageRoot = join(root, ".gorin-release-stage");
  await rm(stageRoot, { recursive: true, force: true });
  await mkdir(stageRoot, { recursive: true });
  const versionById = new Map(plan.skills.map((skill) => [skill.id, skill.to]));
  const stagedSkills = context.skills.map((skill) => withVersion(skill, versionById));

  try {
    const catalog = buildCatalog(
      stagedSkills,
      context.externalSources,
      plan.repository.to,
    );
    const catalogPath = join(stageRoot, "catalog", "index.json");
    await mkdir(dirname(catalogPath), { recursive: true });
    const catalogSource = `${JSON.stringify(catalog, null, 2)}\n`;
    await writeFile(catalogPath, catalogSource);
    const documentationPath = join(stageRoot, "docs", "skills", "index.md");
    await mkdir(dirname(documentationPath), { recursive: true });
    await writeFile(
      documentationPath,
      renderDocumentationIndex(stagedSkills, context.externalSources),
    );
    const baselineOutput = join(
      stageRoot,
      "release",
      "baselines",
      `catalog-${plan.repository.to}.json`,
    );
    if (
      await exists(
        join(root, "release", "baselines", `catalog-${plan.repository.to}.json`),
      )
    ) {
      throw new Error(`Lifecycle baseline already exists for ${plan.repository.to}`);
    }
    await mkdir(dirname(baselineOutput), { recursive: true });
    await writeFile(baselineOutput, catalogSource);

    const profileOutput = join(stageRoot, "release", "profiles");
    await mkdir(profileOutput, { recursive: true });
    for (const filename of await listYamlFiles(join(root, "profiles"))) {
      const name = filename.slice(0, -".yaml".length);
      const resolved = await resolveProfile(root, stagedSkills, name);
      const lock = { ...resolved, repository_version: plan.repository.to };
      await writeFile(
        join(profileOutput, `${name}.lock.json`),
        `${JSON.stringify(lock, null, 2)}\n`,
      );
    }

    const packageOutput = join(stageRoot, "release", "packages");
    await mkdir(packageOutput, { recursive: true });
    for (const skill of stagedSkills) {
      await buildSkillPackages(stagedSkills, skill.skillName, packageOutput);
    }

    const manifestOutput = join(stageRoot, "manifests");
    await mkdir(manifestOutput, { recursive: true });
    for (const change of plan.skills) {
      const skill = context.skills.find((candidate) => candidate.skillName === change.id);
      const source = await readFile(join(skill.skillDir, "manifest.yaml"), "utf8");
      const rendered = source.replace(
        /^version:\s*[^\r\n]+$/m,
        `version: ${change.to}`,
      );
      if (rendered === source) throw new Error(`${change.id}: cannot update manifest version`);
      await writeFile(join(manifestOutput, `${change.id}.yaml`), rendered);
    }

    const repositoryOutput = join(stageRoot, "release", "repository.yaml");
    await mkdir(dirname(repositoryOutput), { recursive: true });
    await writeFile(
      repositoryOutput,
      `schema_version: 1\nversion: ${plan.repository.to}\n`,
    );

    const changelogPath = join(root, "CHANGELOG.md");
    const previousChangelog = await readFile(changelogPath, "utf8").catch((error) => {
      if (error.code === "ENOENT") return "";
      throw error;
    });
    await writeFile(
      join(stageRoot, "CHANGELOG.md"),
      renderChangelog(previousChangelog, plan, context.fragments),
    );

    const consumedOutput = join(
      stageRoot,
      "release",
      "consumed",
      plan.repository.to,
    );
    if (await exists(join(root, "release", "consumed", plan.repository.to))) {
      throw new Error(`Consumed release directory already exists for ${plan.repository.to}`);
    }
    await mkdir(consumedOutput, { recursive: true });
    for (const fragment of context.fragments) {
      await writeFile(join(consumedOutput, fragment.name), fragment.source);
    }
  } catch (error) {
    await rm(stageRoot, { recursive: true, force: true });
    throw error;
  }

  return { stageRoot, stagedSkills };
}

async function commitTransaction(root, operations) {
  const backupRoot = join(root, ".gorin-release-backup");
  await rm(backupRoot, { recursive: true, force: true });
  await mkdir(backupRoot, { recursive: true });
  const applied = [];

  try {
    for (let index = 0; index < operations.length; index += 1) {
      const operation = operations[index];
      const backup = join(backupRoot, String(index));
      const hadDestination = await exists(operation.destination);
      if (hadDestination) {
        await mkdir(dirname(backup), { recursive: true });
        await rename(operation.destination, backup);
      }
      if (operation.staged) {
        await mkdir(dirname(operation.destination), { recursive: true });
        await rename(operation.staged, operation.destination);
      }
      applied.push({ ...operation, backup, hadDestination });
    }
  } catch (error) {
    for (const operation of applied.reverse()) {
      await rm(operation.destination, { recursive: true, force: true });
      if (operation.hadDestination) {
        await mkdir(dirname(operation.destination), { recursive: true });
        await rename(operation.backup, operation.destination);
      }
    }
    await rm(backupRoot, { recursive: true, force: true });
    throw error;
  }
  await rm(backupRoot, { recursive: true, force: true });
}

export async function applyRelease(root, computed) {
  const { plan, context } = computed;
  const { stageRoot } = await stageRelease(root, computed);
  const operations = [];
  for (const change of plan.skills) {
    const skill = context.skills.find((candidate) => candidate.skillName === change.id);
    operations.push({
      destination: join(skill.skillDir, "manifest.yaml"),
      staged: join(stageRoot, "manifests", `${change.id}.yaml`),
    });
  }
  operations.push(
    {
      destination: join(root, "release", "repository.yaml"),
      staged: join(stageRoot, "release", "repository.yaml"),
    },
    {
      destination: join(root, "catalog", "index.json"),
      staged: join(stageRoot, "catalog", "index.json"),
    },
    {
      destination: join(root, "docs", "skills", "index.md"),
      staged: join(stageRoot, "docs", "skills", "index.md"),
    },
    {
      destination: join(
        root,
        "release",
        "baselines",
        `catalog-${plan.repository.to}.json`,
      ),
      staged: join(
        stageRoot,
        "release",
        "baselines",
        `catalog-${plan.repository.to}.json`,
      ),
    },
    {
      destination: join(root, "release", "profiles"),
      staged: join(stageRoot, "release", "profiles"),
    },
    {
      destination: join(root, "release", "packages"),
      staged: join(stageRoot, "release", "packages"),
    },
    {
      destination: join(root, "CHANGELOG.md"),
      staged: join(stageRoot, "CHANGELOG.md"),
    },
    {
      destination: join(root, "release", "consumed", plan.repository.to),
      staged: join(stageRoot, "release", "consumed", plan.repository.to),
    },
  );
  for (const fragment of context.fragments) {
    operations.push({ destination: fragment.path });
  }

  try {
    await commitTransaction(root, operations);
  } finally {
    await rm(stageRoot, { recursive: true, force: true });
  }
  return plan;
}

export async function verifyRelease(root, computed) {
  const { stageRoot } = await stageRelease(root, computed);
  try {
    const requiredArtifacts = [
      join(stageRoot, "CHANGELOG.md"),
      join(stageRoot, "catalog", "index.json"),
      join(stageRoot, "docs", "skills", "index.md"),
      join(stageRoot, "release", "repository.yaml"),
      join(
        stageRoot,
        "release",
        "baselines",
        `catalog-${computed.plan.repository.to}.json`,
      ),
      join(stageRoot, "release", "profiles"),
      join(stageRoot, "release", "packages"),
    ];
    for (const artifact of requiredArtifacts) {
      if (!(await exists(artifact))) {
        throw new Error(`Release dry-run did not generate ${relative(root, artifact)}`);
      }
    }

    const catalog = JSON.parse(
      await readFile(join(stageRoot, "catalog", "index.json"), "utf8"),
    );
    if (catalog.catalog_version !== computed.plan.repository.to) {
      throw new Error("Release dry-run catalog version diverges from the release plan");
    }
    for (const change of computed.plan.skills) {
      const catalogSkill = catalog.skills.find((skill) => skill.id === change.id);
      if (catalogSkill?.version !== change.to) {
        throw new Error(`Release dry-run catalog version diverges for ${change.id}`);
      }
    }
    return computed.plan;
  } finally {
    await rm(stageRoot, { recursive: true, force: true });
  }
}
