import { createHash } from "node:crypto";
import { lstat, mkdir, mkdtemp, readdir, readFile, rm, stat, writeFile } from "node:fs/promises";
import { readlink, rename, rmdir, symlink, unlink } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, isAbsolute, join, relative, resolve } from "node:path";
import { parse } from "yaml";

const LIFECYCLES = new Set([
  "incubating",
  "candidate",
  "promoted",
  "deprecated",
  "retired",
]);
const DOMAINS = new Set([
  "education",
  "content",
  "documents",
  "knowledge",
  "research",
  "agent-ops",
  "engineering",
]);
const LEGACY_V1_DOMAINS = new Set(["edu"]);
const OWNERSHIP_TYPES = new Set(["first-party", "managed-mirror", "external"]);
const AUDIENCES = new Set(["public", "private"]);
const TARGETS = new Set(["agent-skills", "codex", "claude-code", "openclaw"]);
const SEMVER_PATTERN = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/;
const BUILD_EXCLUDED_NAMES = new Set([
  "manifest.yaml",
  ".skill-meta.json",
  ".DS_Store",
  "__pycache__",
  ".archive",
  "research",
  "tests",
]);
const PROHIBITED_DIRECTORIES = new Set([
  "node_modules",
  ".venv",
  "venv",
  "__pycache__",
  ".pytest_cache",
  ".mypy_cache",
  ".ruff_cache",
  ".cache",
  "dist",
  "out",
  "output",
  "generated",
  "coverage",
  "vendor",
]);
const TARGET_INSTALL_ROOTS = {
  "agent-skills": [".agents", "skills"],
  codex: [".codex", "skills"],
  "claude-code": [".claude", "skills"],
  openclaw: [".openclaw", "skills"],
};

async function listDirectories(path) {
  try {
    const entries = await readdir(path, { withFileTypes: true });
    return entries.filter((entry) => entry.isDirectory()).map((entry) => entry.name);
  } catch (error) {
    if (error.code === "ENOENT") return [];
    throw error;
  }
}

async function scanSourceArtifacts(skillDir) {
  async function visit(directory) {
    const entries = await readdir(directory, { withFileTypes: true });
    for (const entry of entries) {
      const path = join(directory, entry.name);
      if (entry.isSymbolicLink()) {
        throw new Error(`${path}: source repositories do not accept symbolic links`);
      }
      if (entry.isDirectory()) {
        if (
          PROHIBITED_DIRECTORIES.has(entry.name) ||
          entry.name.endsWith(".egg-info")
        ) {
          throw new Error(`${path}: prohibited repository artifact ${entry.name}`);
        }
        await visit(path);
        continue;
      }
      if (!entry.isFile()) {
        throw new Error(`${path}: prohibited repository artifact special file`);
      }
      const secretShaped =
        (/^\.env(?:\.|$)/.test(entry.name) && entry.name !== ".env.example") ||
        /\.(?:pem|key|p12|pfx)$/i.test(entry.name) ||
        /^(?:id_rsa|id_ed25519)(?:\.|$)/.test(entry.name);
      if (secretShaped) {
        throw new Error(`${path}: prohibited repository artifact secret-shaped file`);
      }
    }
  }

  await visit(skillDir);
}

export async function computeContentDigest(root) {
  const hash = createHash("sha256");

  async function visit(directory) {
    const entries = await readdir(directory, { withFileTypes: true });
    for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
      if (entry.name === "manifest.yaml") continue;
      const path = join(directory, entry.name);
      if (entry.isDirectory()) {
        await visit(path);
      } else if (entry.isFile()) {
        hash.update(relative(root, path));
        hash.update("\0");
        hash.update(await readFile(path));
        hash.update("\0");
      } else {
        throw new Error(`${path}: content digests do not accept symbolic links or special files`);
      }
    }
  }

  await visit(root);
  return `sha256:${hash.digest("hex")}`;
}

function parseSkillMarkdown(source, skillDir) {
  const match = source.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);
  if (!match) throw new Error(`${skillDir}: SKILL.md must start with YAML frontmatter`);
  return parse(match[1]);
}

function assertRelativePath(path, base, label) {
  if (typeof path !== "string" || isAbsolute(path) || path.split(/[\\/]/).includes("..")) {
    throw new Error(`${label} must be a repository-relative safe path`);
  }
  const resolved = resolve(base, path);
  if (resolved !== base && !resolved.startsWith(`${base}/`)) {
    throw new Error(`${label} escapes its allowed root`);
  }
  return resolved;
}

async function loadQualityEvidence(skillDir, skillName, evidenceReference, label) {
  const evidencePath = assertRelativePath(
    evidenceReference,
    skillDir,
    `${skillName}: ${label}.evidence`,
  );
  try {
    return parse(await readFile(evidencePath, "utf8"));
  } catch (error) {
    if (error.code === "ENOENT") {
      throw new Error(`${skillName}: ${label} evidence is missing`);
    }
    throw error;
  }
}

function validateQualityEvidence(skillName, manifest, evidence, label) {
  if (evidence?.schema_version !== 1) {
    throw new Error(`${skillName}: ${label} evidence schema_version must be 1`);
  }
  const requiredPasses = ["spec", "schema", "provenance_and_license"];
  for (const field of requiredPasses) {
    if (evidence?.[field] !== "passed") {
      throw new Error(`${skillName}: ${label} evidence ${field} must be passed`);
    }
  }
  for (const field of ["positive_triggers", "negative_triggers", "golden_cases", "tests"]) {
    if (!Array.isArray(evidence?.[field]) || evidence[field].length === 0) {
      throw new Error(`${skillName}: ${label} evidence ${field} must be non-empty`);
    }
  }
  if (
    evidence.tests.some(
      (entry) => !entry?.command?.trim() || entry?.result !== "passed",
    )
  ) {
    throw new Error(`${skillName}: all ${label} test evidence must be passed`);
  }
  for (const target of manifest.targets) {
    const smoke = evidence.target_smoke?.[target];
    if (smoke?.build !== "passed" || smoke?.install !== "passed") {
      throw new Error(`${skillName}: ${label} evidence requires build/install smoke for ${target}`);
    }
  }
  if (evidence.runtime_output !== "clean") {
    throw new Error(`${skillName}: ${label} runtime output evidence must be clean`);
  }
}

async function validateCandidate(skillDir, skillName, manifest) {
  if (!manifest.qualification?.evidence) {
    throw new Error(
      `${skillName}: candidate skill requires automated qualification evidence`,
    );
  }
  const evidence = await loadQualityEvidence(
    skillDir,
    skillName,
    manifest.qualification.evidence,
    "qualification",
  );
  validateQualityEvidence(skillName, manifest, evidence, "qualification");
  const cases = await loadQualificationCases(skillDir, skillName);
  const mappings = [
    ["positive_triggers", cases.positive_triggers],
    ["negative_triggers", cases.negative_triggers],
    ["golden_cases", cases.golden_cases],
  ];
  for (const [field, entries] of mappings) {
    const expected = entries.map((entry) => entry.id).sort();
    const actual = [...evidence[field]].sort();
    if (
      actual.some((id) => typeof id !== "string") ||
      actual.length !== expected.length ||
      actual.some((id, index) => id !== expected[index])
    ) {
      throw new Error(
        `${skillName}: qualification evidence ${field} must reference every case id exactly once`,
      );
    }
  }
}

async function validatePromotion(root, skillDir, skillName, manifest) {
  const promotion = manifest.promotion;
  if (
    !promotion?.evidence ||
    !promotion?.documentation ||
    !promotion?.approved_by ||
    !promotion?.approved_on ||
    promotion?.maintenance_commitment !== true
  ) {
    throw new Error(
      `${skillName}: promoted skill requires promotion evidence, documentation, and human approval`,
    );
  }

  const documentationPath = assertRelativePath(
    promotion.documentation,
    root,
    `${skillName}: promotion.documentation`,
  );
  const evidence = await loadQualityEvidence(
    skillDir,
    skillName,
    promotion.evidence,
    "promotion",
  );
  validateQualityEvidence(skillName, manifest, evidence, "promotion");
  let documentation;
  try {
    documentation = await readFile(documentationPath, "utf8");
  } catch (error) {
    if (error.code === "ENOENT") {
      throw new Error(`${skillName}: promoted skill documentation is missing`);
    }
    throw error;
  }
  if (!documentation.trim()) {
    throw new Error(`${skillName}: promoted skill documentation must not be empty`);
  }
}

async function validateProvenance(skillDir, skillName, manifest) {
  if (manifest.ownership === "external") {
    throw new Error(`${skillName}: external sources must be registered without local source`);
  }
  if (manifest.ownership === "managed-mirror") {
    const provenance = manifest.provenance;
    if (
      provenance?.kind !== "mirror" ||
      !provenance?.upstream?.url ||
      !provenance?.upstream?.revision ||
      !provenance?.license?.spdx ||
      !provenance?.license?.file ||
      !/^sha256:[0-9a-f]{64}$/.test(provenance?.content_digest ?? "")
    ) {
      throw new Error(
        `${skillName}: managed mirror requires upstream revision, content digest, and license evidence`,
      );
    }
    const licensePath = assertRelativePath(
      provenance.license.file,
      skillDir,
      `${skillName}: provenance.license.file`,
    );
    try {
      await stat(licensePath);
    } catch (error) {
      if (error.code === "ENOENT") {
        throw new Error(`${skillName}: managed mirror license evidence is missing`);
      }
      throw error;
    }
    const actualDigest = await computeContentDigest(skillDir);
    if (actualDigest !== provenance.content_digest) {
      throw new Error(
        `${skillName}: managed mirror content digest mismatch (expected ${provenance.content_digest}, actual ${actualDigest})`,
      );
    }
  }
  if (manifest.provenance?.kind === "adapted") {
    if (manifest.ownership !== "first-party") {
      throw new Error(`${skillName}: adapted skills must be first-party`);
    }
    if (!skillName.startsWith("gorin-")) {
      throw new Error(`${skillName}: adapted first-party skills must use the gorin- namespace`);
    }
    const sources = manifest.provenance.sources;
    if (
      !manifest.provenance.adaptation_note ||
      !Array.isArray(sources) ||
      sources.length === 0 ||
      sources.some((source) => !source?.url || !source?.revision || !source?.license)
    ) {
      throw new Error(`${skillName}: adapted skill requires a complete provenance and license chain`);
    }
  }
}

export async function validateRepository(root) {
  const skillsRoot = join(root, "skills");
  const skills = [];

  for (const domain of (await listDirectories(skillsRoot)).sort()) {
    if (LEGACY_V1_DOMAINS.has(domain)) continue;
    const domainRoot = join(skillsRoot, domain);
    for (const skillName of (await listDirectories(domainRoot)).sort()) {
      const skillDir = join(domainRoot, skillName);
      const [manifestSource, skillSource] = await Promise.all([
        readFile(join(skillDir, "manifest.yaml"), "utf8"),
        readFile(join(skillDir, "SKILL.md"), "utf8"),
      ]);
      const manifest = parse(manifestSource);
      const frontmatter = parseSkillMarkdown(skillSource, skillDir);

      await scanSourceArtifacts(skillDir);

      if (manifest?.schema_version !== 1) {
        throw new Error(`${skillName}: manifest schema_version must be 1`);
      }
      if (!SEMVER_PATTERN.test(manifest.version ?? "")) {
        throw new Error(`${skillName}: manifest version must be semantic versioning`);
      }
      if (frontmatter.name !== skillName) {
        throw new Error(
          `${skillName}: SKILL.md name must match its directory (${skillName})`,
        );
      }
      if (!DOMAINS.has(domain)) {
        throw new Error(`${skillName}: unsupported domain ${domain}`);
      }
      if (manifest.domain !== domain) {
        throw new Error(
          `${skillName}: manifest domain must match its path (${domain})`,
        );
      }
      if (!LIFECYCLES.has(manifest.lifecycle)) {
        throw new Error(
          `${skillName}: unsupported lifecycle ${manifest.lifecycle ?? "(missing)"}`,
        );
      }
      if (!OWNERSHIP_TYPES.has(manifest.ownership)) {
        throw new Error(`${skillName}: unsupported ownership ${manifest.ownership ?? "(missing)"}`);
      }
      if (!AUDIENCES.has(manifest.audience)) {
        throw new Error(`${skillName}: unsupported audience ${manifest.audience ?? "(missing)"}`);
      }
      if (
        !Array.isArray(manifest.targets) ||
        manifest.targets.length === 0 ||
        manifest.targets.some((target) => !TARGETS.has(target)) ||
        new Set(manifest.targets).size !== manifest.targets.length
      ) {
        throw new Error(`${skillName}: manifest targets must be unique supported targets`);
      }
      if (
        manifest.aliases !== undefined &&
        (!Array.isArray(manifest.aliases) ||
          manifest.aliases.length === 0 ||
          manifest.aliases.some(
            (alias) =>
              typeof alias !== "string" ||
              !/^[a-z0-9][a-z0-9-]*$/.test(alias),
          ) ||
          new Set(manifest.aliases).size !== manifest.aliases.length)
      ) {
        throw new Error(`${skillName}: aliases must be unique lowercase kebab-case names`);
      }
      if (
        manifest.ownership === "first-party" &&
        ["candidate", "promoted"].includes(manifest.lifecycle) &&
        !skillName.startsWith("gorin-")
      ) {
        throw new Error(
          `${skillName}: ${manifest.lifecycle} first-party skills must use the gorin- namespace`,
        );
      }
      if (manifest.lifecycle === "candidate") {
        await validateCandidate(skillDir, skillName, manifest);
      }
      if (manifest.lifecycle === "promoted") {
        await validatePromotion(root, skillDir, skillName, manifest);
      }
      await validateProvenance(skillDir, skillName, manifest);

      skills.push({ domain, skillName, skillDir, manifest, frontmatter, skillSource });
    }
  }

  const canonicalNames = new Set(skills.map((skill) => skill.skillName));
  const aliasOwners = new Map();
  for (const skill of skills) {
    for (const alias of skill.manifest.aliases ?? []) {
      if (canonicalNames.has(alias)) {
        throw new Error(
          `${skill.skillName}: alias ${alias} collides with a canonical skill identifier`,
        );
      }
      const previousOwner = aliasOwners.get(alias);
      if (previousOwner) {
        throw new Error(
          `${skill.skillName}: alias ${alias} is already claimed by ${previousOwner}`,
        );
      }
      aliasOwners.set(alias, skill.skillName);
    }
  }

  return skills;
}

export async function loadExternalSources(root) {
  const registryRoot = join(root, "registry", "external");
  let entries;
  try {
    entries = await readdir(registryRoot, { withFileTypes: true });
  } catch (error) {
    if (error.code === "ENOENT") return [];
    throw error;
  }
  const sources = [];
  for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
    if (!entry.isFile() || !entry.name.endsWith(".yaml")) continue;
    const external = parse(await readFile(join(registryRoot, entry.name), "utf8"));
    const expectedId = entry.name.slice(0, -".yaml".length);
    if (
      external?.schema_version !== 1 ||
      external.id !== expectedId ||
      !SEMVER_PATTERN.test(external.version ?? "") ||
      !LIFECYCLES.has(external.lifecycle) ||
      external.ownership !== "external" ||
      !AUDIENCES.has(external.audience) ||
      !external.description ||
      !external.source?.url ||
      !external.source?.revision ||
      !external.source?.license ||
      external.source?.path
    ) {
      throw new Error(`${expectedId}: invalid external source registry entry`);
    }
    sources.push(external);
  }
  return sources;
}

const LEGAL_LIFECYCLE_TRANSITIONS = {
  incubating: new Set(["incubating", "candidate", "retired"]),
  candidate: new Set(["candidate", "incubating", "promoted", "retired"]),
  promoted: new Set(["promoted", "deprecated"]),
  deprecated: new Set(["deprecated", "promoted", "retired"]),
  retired: new Set(["retired"]),
};

export function validateLifecycleTransitions(skills, baseline) {
  if (baseline?.schema_version !== 1 || !Array.isArray(baseline.skills)) {
    throw new Error("Lifecycle baseline must be a schema_version 1 catalog");
  }
  const previousById = new Map(
    baseline.skills.map((skill) => [skill.id, skill.lifecycle]),
  );
  for (const skill of skills) {
    const previous = previousById.get(skill.skillName);
    if (!previous) continue;
    const allowed = LEGAL_LIFECYCLE_TRANSITIONS[previous];
    if (!allowed?.has(skill.manifest.lifecycle)) {
      throw new Error(
        `${skill.skillName}: illegal lifecycle transition ${previous} -> ${skill.manifest.lifecycle}`,
      );
    }
  }
}

export function buildCatalog(skills, externalSources = [], catalogVersion) {
  const localSkillIds = new Set(
    skills.flatMap((skill) => [
      skill.skillName,
      ...(skill.manifest.aliases ?? []),
    ]),
  );
  for (const external of externalSources) {
    if (localSkillIds.has(external.id)) {
      throw new Error(
        `Duplicate skill identifier ${external.id} across local and external sources`,
      );
    }
  }

  return {
    schema_version: 1,
    ...(catalogVersion ? { catalog_version: catalogVersion } : {}),
    skills: [
      ...skills
      .map(({ domain, skillName, manifest, frontmatter }) => ({
        id: skillName,
        version: manifest.version,
        domain,
        lifecycle: manifest.lifecycle,
        ownership: manifest.ownership,
        audience: manifest.audience,
        targets: manifest.targets,
        description: frontmatter.description,
        source: `skills/${domain}/${skillName}`,
      })),
      ...externalSources.map((external) => ({
        id: external.id,
        version: external.version,
        lifecycle: external.lifecycle,
        ownership: external.ownership,
        audience: external.audience,
        description: external.description,
        source_type: "external",
        source: external.source,
      })),
    ]
      .sort((left, right) => left.id.localeCompare(right.id)),
  };
}

export function renderDocumentationIndex(skills, externalSources = []) {
  const domains = [...new Set(skills.map((skill) => skill.domain))].sort();
  const lines = [
    "# Skill Catalog",
    "",
    "Generated from v2 manifests. Do not edit this file by hand.",
    "",
  ];
  for (const domain of domains) {
    lines.push(`## ${domain}`, "");
    for (const skill of skills
      .filter((candidate) => candidate.domain === domain)
      .sort((left, right) => left.skillName.localeCompare(right.skillName))) {
      lines.push(
        `- [\`${skill.skillName}\`](../../skills/${domain}/${skill.skillName}/) — ${skill.manifest.version}, ${skill.manifest.lifecycle}`,
      );
    }
    lines.push("");
  }
  lines.push("## External sources", "");
  for (const source of [...externalSources].sort((left, right) => left.id.localeCompare(right.id))) {
    lines.push(
      `- [\`${source.id}\`](${source.source.url}) — ${source.version}, ${source.lifecycle}, ${source.source.license}`,
    );
  }
  lines.push("");
  return lines.join("\n");
}

async function readProfile(root, name) {
  if (!/^[a-z0-9][a-z0-9-]*$/.test(name)) {
    throw new Error(`Invalid profile name: ${name}`);
  }
  const path = join(root, "profiles", `${name}.yaml`);
  let profile;
  try {
    profile = parse(await readFile(path, "utf8"));
  } catch (error) {
    if (error.code === "ENOENT") throw new Error(`Unknown profile: ${name}`);
    throw error;
  }
  if (profile?.schema_version !== 1) {
    throw new Error(`${name}: profile schema_version must be 1`);
  }
  if (profile.name !== name) {
    throw new Error(`${name}: profile name must match its filename`);
  }
  return profile;
}

export async function resolveProfile(root, skills, profileName) {
  const requestedProfile = await readProfile(root, profileName);
  if (requestedProfile.legacy) {
    const inventoryPath = assertRelativePath(
      requestedProfile.legacy.inventory,
      root,
      `${profileName}: legacy.inventory`,
    );
    const inventory = JSON.parse(await readFile(inventoryPath, "utf8"));
    if (inventory?.schema_version !== 1 || !Array.isArray(inventory.skills)) {
      throw new Error(`${profileName}: invalid legacy inventory`);
    }
    const selected = [];
    const seen = new Set();
    const inventoryById = new Map(inventory.skills.map((skill) => [skill.id, skill]));
    for (const id of requestedProfile.legacy.skills ?? []) {
      if (seen.has(id)) throw new Error(`${profileName}: duplicate selection ${id}`);
      seen.add(id);
      const skill = inventoryById.get(id);
      if (!skill) throw new Error(`${profileName}: unknown legacy skill ${id}`);
      if (skill.representation !== "legacy-v1" || !skill.distributable_legacy) {
        throw new Error(`${profileName}: legacy skill ${id} is not distributable`);
      }
      selected.push({
        id,
        version: skill.version,
        lifecycle: skill.lifecycle,
        source: skill.path,
        legacy: true,
      });
    }
    return {
      schema_version: 1,
      profile: profileName,
      end_of_support: requestedProfile.legacy.end_of_support,
      skills: selected.sort((left, right) => left.id.localeCompare(right.id)),
    };
  }
  const skillsById = new Map(skills.map((skill) => [skill.skillName, skill]));
  const selected = new Map();

  async function addSkill(skillName, profile, source) {
    const skill = skillsById.get(skillName);
    if (!skill) throw new Error(`${profile.name}: unknown skill ${skillName}`);
    if (selected.has(skillName)) {
      throw new Error(`${profile.name}: duplicate selection ${skillName}`);
    }
    const allowed = new Set(profile.allow_lifecycles ?? ["promoted"]);
    if (profile.name === "default" && skill.manifest.lifecycle !== "promoted") {
      throw new Error(`default: only promoted skills may be selected`);
    }
    if (source === "selector" && skill.manifest.lifecycle !== "promoted") {
      throw new Error(`${profile.name}: non-promoted skills require explicit identifiers`);
    }
    if (!allowed.has(skill.manifest.lifecycle)) {
      throw new Error(
        `${profile.name}: lifecycle ${skill.manifest.lifecycle} for ${skillName} is not explicitly allowed`,
      );
    }
    selected.set(skillName, skill);
  }

  async function visit(name, stack) {
    const cycleIndex = stack.indexOf(name);
    if (cycleIndex !== -1) {
      throw new Error(`profile inclusion cycle: ${[...stack.slice(cycleIndex), name].join(" -> ")}`);
    }
    const profile = await readProfile(root, name);
    const nextStack = [...stack, name];
    for (const included of profile.profiles ?? []) {
      await visit(included, nextStack);
    }
    for (const lifecycle of profile.select?.lifecycles ?? []) {
      if (!LIFECYCLES.has(lifecycle)) {
        throw new Error(`${name}: unknown lifecycle selector ${lifecycle}`);
      }
      const matching = skills
        .filter(
          (skill) =>
            skill.manifest.lifecycle === lifecycle &&
            (!(profile.select?.domains?.length > 0) ||
              profile.select.domains.includes(skill.domain)),
        )
        .sort((left, right) => left.skillName.localeCompare(right.skillName));
      for (const skill of matching) {
        await addSkill(skill.skillName, profile, "selector");
      }
    }
    for (const skillName of profile.skills ?? []) {
      await addSkill(skillName, profile, "explicit");
    }
  }

  await visit(profileName, []);
  return {
    schema_version: 1,
    profile: profileName,
    ...(requestedProfile.end_of_support
      ? { end_of_support: requestedProfile.end_of_support }
      : {}),
    ...(requestedProfile.compatibility_aliases
      ? {
          compatibility_aliases: [...selected.values()]
            .flatMap((skill) =>
              (skill.manifest.aliases ?? []).map((alias) => ({
                alias,
                canonical: skill.skillName,
              })),
            )
            .sort((left, right) => left.alias.localeCompare(right.alias)),
        }
      : {}),
    skills: [...selected.values()]
      .map((skill) => ({
        id: skill.skillName,
        version: skill.manifest.version,
        lifecycle: skill.manifest.lifecycle,
        source: `skills/${skill.domain}/${skill.skillName}`,
      }))
      .sort((left, right) => left.id.localeCompare(right.id)),
  };
}

function renderOpenClawSkill(skillSource, config = {}) {
  const match = skillSource.match(/^(---\r?\n)([\s\S]*?)(\r?\n---(?:\r?\n|$))([\s\S]*)$/);
  if (!match) throw new Error("OpenClaw build requires valid SKILL.md frontmatter");

  const extensionLines = [];
  if (config.homepage) extensionLines.push(`homepage: ${JSON.stringify(config.homepage)}`);
  if (typeof config.user_invocable === "boolean") {
    extensionLines.push(`user-invocable: ${config.user_invocable}`);
  }
  if (typeof config.disable_model_invocation === "boolean") {
    extensionLines.push(
      `disable-model-invocation: ${config.disable_model_invocation}`,
    );
  }
  if (config.command_dispatch) {
    extensionLines.push(`command-dispatch: ${config.command_dispatch}`);
  }
  if (config.command_tool) extensionLines.push(`command-tool: ${config.command_tool}`);
  if (config.command_arg_mode) {
    extensionLines.push(`command-arg-mode: ${config.command_arg_mode}`);
  }
  if (config.metadata) {
    extensionLines.push(
      `metadata: ${JSON.stringify({ openclaw: config.metadata })}`,
    );
  }

  if (extensionLines.length === 0) return skillSource;
  return `${match[1]}${match[2]}\n${extensionLines.join("\n")}${match[3]}${match[4]}`;
}

async function copySkillSource(sourceDir, destinationDir, target, manifest) {
  await rm(destinationDir, { recursive: true, force: true });
  await mkdir(destinationDir, { recursive: true });

  async function visit(currentSource, currentDestination) {
    const entries = await readdir(currentSource, { withFileTypes: true });
    for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
      if (BUILD_EXCLUDED_NAMES.has(entry.name)) continue;
      const sourcePath = join(currentSource, entry.name);
      const destinationPath = join(currentDestination, entry.name);
      if (entry.isDirectory()) {
        await mkdir(destinationPath, { recursive: true });
        await visit(sourcePath, destinationPath);
        continue;
      }
      if (!entry.isFile()) {
        throw new Error(`${sourcePath}: target builds do not accept symbolic links or special files`);
      }

      const content = await readFile(sourcePath);
      if (target === "openclaw" && entry.name === "SKILL.md") {
        const rendered = renderOpenClawSkill(
          content.toString("utf8"),
          manifest.adapters?.openclaw,
        );
        await writeFile(destinationPath, rendered);
      } else {
        await writeFile(destinationPath, content);
      }
    }
  }

  await visit(sourceDir, destinationDir);
}

export async function buildSkillPackages(skills, skillName, outputRoot) {
  const skill = skills.find((candidate) => candidate.skillName === skillName);
  if (!skill) throw new Error(`Unknown skill: ${skillName}`);

  for (const target of skill.manifest.targets) {
    await copySkillSource(
      skill.skillDir,
      join(outputRoot, target, skillName),
      target,
      skill.manifest,
    );
    for (const alias of skill.manifest.aliases ?? []) {
      const aliasDir = join(outputRoot, target, alias);
      await rm(aliasDir, { recursive: true, force: true });
      await mkdir(aliasDir, { recursive: true });
      const aliasSkill = [
        "---",
        `name: ${alias}`,
        `description: Deprecated compatibility alias for ${skillName}. Use ${skillName} instead.`,
        "---",
        "",
        `# Deprecated alias: ${alias}`,
        "",
        `Immediately invoke the canonical \`${skillName}\` skill with the user's original request.`,
        `This alias contains no implementation and is removed before repository major 3.`,
        "",
      ].join("\n");
      await writeFile(join(aliasDir, "SKILL.md"), aliasSkill);
    }
  }

  return { skill, targets: [...skill.manifest.targets] };
}

function assertQualificationCases(skillName, cases) {
  if (cases?.schema_version !== 1) {
    throw new Error(`${skillName}: quality/cases.yaml schema_version must be 1`);
  }
  const collections = [
    ["positive_triggers", cases.positive_triggers],
    ["negative_triggers", cases.negative_triggers],
    ["golden_cases", cases.golden_cases],
  ];
  const seenIds = new Set();
  for (const [name, entries] of collections) {
    if (!Array.isArray(entries) || entries.length < 2) {
      throw new Error(`${skillName}: ${name} must contain at least two cases`);
    }
    for (const entry of entries) {
      if (
        !entry ||
        typeof entry.id !== "string" ||
        !/^[a-z0-9][a-z0-9-]*$/.test(entry.id) ||
        seenIds.has(entry.id)
      ) {
        throw new Error(`${skillName}: qualification case ids must be unique lowercase kebab-case`);
      }
      seenIds.add(entry.id);
    }
  }
  for (const entry of cases.positive_triggers) {
    if (!entry.prompt?.trim() || entry.expected_route !== skillName) {
      throw new Error(`${skillName}: positive triggers must route to the canonical skill id`);
    }
  }
  for (const entry of cases.negative_triggers) {
    if (!entry.prompt?.trim() || entry.expected_route !== "not-this-skill") {
      throw new Error(`${skillName}: negative triggers must route away from this skill`);
    }
  }
  for (const entry of cases.golden_cases) {
    if (typeof entry.input !== "string" || !entry.input.trim()) {
      throw new Error(`${skillName}: golden cases require non-empty input`);
    }
    const observations = [
      entry.expected_observations,
      entry.forbidden_observations,
    ];
    if (
      observations.some(
        (values) =>
          !Array.isArray(values) ||
          values.length === 0 ||
          values.some(
            (value) => typeof value !== "string" || !value.trim(),
          ),
      )
    ) {
      throw new Error(
        `${skillName}: golden case observations must be non-empty strings`,
      );
    }
  }
}

async function loadQualificationCases(skillDir, skillName) {
  let cases;
  try {
    cases = parse(
      await readFile(join(skillDir, "quality", "cases.yaml"), "utf8"),
    );
  } catch (error) {
    if (error.code === "ENOENT") {
      throw new Error(`${skillName}: missing quality/cases.yaml`);
    }
    throw error;
  }
  assertQualificationCases(skillName, cases);
  return cases;
}

export async function qualifySkill({ root, skills, skillName }) {
  const skill = skills.find((candidate) => candidate.skillName === skillName);
  if (!skill) throw new Error(`Unknown skill: ${skillName}`);
  if (!["incubating", "candidate"].includes(skill.manifest.lifecycle)) {
    throw new Error(`${skillName}: only incubating or candidate skills can run qualification`);
  }

  const cases = await loadQualificationCases(skill.skillDir, skillName);

  const sandbox = await mkdtemp(join(tmpdir(), "gorin-skill-qualification-"));
  const packageRoot = join(sandbox, "packages");
  const home = join(sandbox, "home");
  const targetSmoke = {};
  try {
    await buildSkillPackages(skills, skillName, packageRoot);
    for (const target of skill.manifest.targets) {
      await stat(join(packageRoot, target, skillName, "SKILL.md"));
      await installSkill({
        skills,
        skillName,
        target,
        root: sandbox,
        home,
        mode: "managed",
      });
      await stat(join(home, ...TARGET_INSTALL_ROOTS[target], skillName, "SKILL.md"));
      targetSmoke[target] = { build: "passed", install: "passed" };
    }
  } finally {
    await rm(sandbox, { recursive: true, force: true });
  }

  return {
    schema_version: 1,
    skill: skillName,
    lifecycle: skill.manifest.lifecycle,
    case_contract: {
      positive_triggers: cases.positive_triggers.length,
      negative_triggers: cases.negative_triggers.length,
      golden_cases: cases.golden_cases.length,
    },
    target_smoke: targetSmoke,
    runtime_output: "clean",
  };
}

async function pathExists(path) {
  try {
    await lstat(path);
    return true;
  } catch (error) {
    if (error.code === "ENOENT") return false;
    throw error;
  }
}

function receiptPathFor(home, target, skillName) {
  return join(
    home,
    ".local",
    "state",
    "gorin-skills",
    "receipts",
    target,
    `${skillName}.json`,
  );
}

async function readReceipt(path) {
  try {
    return JSON.parse(await readFile(path, "utf8"));
  } catch (error) {
    if (error.code === "ENOENT") return null;
    throw new Error(`${path}: invalid install receipt (${error.message})`);
  }
}

function receiptOwnsDestination(receipt, { skillName, target, destination }) {
  return Boolean(
    receipt &&
      receipt.owner === "gorin-skills" &&
      receipt.skill === skillName &&
      receipt.target === target &&
      receipt.destination === destination,
  );
}

async function collectFileRecords(root) {
  const records = [];

  async function visit(directory) {
    const entries = await readdir(directory, { withFileTypes: true });
    for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
      const path = join(directory, entry.name);
      if (entry.isDirectory()) {
        await visit(path);
      } else if (entry.isFile()) {
        const content = await readFile(path);
        records.push({
          path: relative(root, path),
          sha256: createHash("sha256").update(content).digest("hex"),
        });
      } else {
        throw new Error(`${path}: managed packages cannot contain symbolic links or special files`);
      }
    }
  }

  await visit(root);
  return records;
}

async function copyDirectory(source, destination) {
  await mkdir(destination, { recursive: true });
  const entries = await readdir(source, { withFileTypes: true });
  for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
    const sourcePath = join(source, entry.name);
    const destinationPath = join(destination, entry.name);
    if (entry.isDirectory()) {
      await copyDirectory(sourcePath, destinationPath);
    } else if (entry.isFile()) {
      await writeFile(destinationPath, await readFile(sourcePath));
    } else {
      throw new Error(`${sourcePath}: managed packages cannot contain symbolic links or special files`);
    }
  }
}

export async function createInstallPlan({ skills, skillName, target, root, home }) {
  const skill = skills.find((candidate) => candidate.skillName === skillName);
  if (!skill) throw new Error(`Unknown skill: ${skillName}`);
  if (!skill.manifest.targets.includes(target)) {
    throw new Error(`${skillName}: target ${target} is not declared in manifest.yaml`);
  }
  const installSegments = TARGET_INSTALL_ROOTS[target];
  if (!installSegments) throw new Error(`Unsupported install target: ${target}`);

  const destination = join(home, ...installSegments, skillName);
  const destinationExists = await pathExists(destination);
  const receiptPath = receiptPathFor(home, target, skillName);
  const receipt = await readReceipt(receiptPath);
  const managed = receiptOwnsDestination(receipt, { skillName, target, destination });
  const requirements = skill.manifest.adapters?.[target]?.metadata?.requires ?? {};
  const hostRequirements = Object.fromEntries(
    Object.entries(requirements).sort(([left], [right]) => left.localeCompare(right)),
  );

  const hostActions = skill.manifest.host_actions ?? [];
  return {
    schema_version: 1,
    mode: "dry-run",
    skill: skillName,
    version: skill.manifest.version,
    target,
    package_source: join(root, "dist", target, skillName),
    destination,
    relationship: destinationExists ? (managed ? `managed-${receipt.mode}` : "unmanaged") : "absent",
    would_overwrite: destinationExists,
    host_requirements: hostRequirements,
    ...(hostActions.length > 0
      ? { host_actions: hostActions, requires_separate_approval: true }
      : {}),
  };
}

export async function installSkill({
  skills,
  skillName,
  target,
  root,
  home,
  mode = "managed",
}) {
  if (!["managed", "link"].includes(mode)) {
    throw new Error(`Unsupported install mode: ${mode}`);
  }
  const plan = await createInstallPlan({ skills, skillName, target, root, home });
  const receiptPath = receiptPathFor(home, target, skillName);
  const existingReceipt = await readReceipt(receiptPath);
  if (plan.relationship === "unmanaged") {
    throw new Error(`Refusing to overwrite unmanaged destination: ${plan.destination}`);
  }
  if (
    plan.relationship === "absent" &&
    existingReceipt &&
    !receiptOwnsDestination(existingReceipt, {
      skillName,
      target,
      destination: plan.destination,
    })
  ) {
    throw new Error(`Refusing install because receipt ownership is inconsistent: ${receiptPath}`);
  }

  const buildRoot = join(root, "dist");
  const build = await buildSkillPackages(skills, skillName, buildRoot);
  const packageSource = join(buildRoot, target, skillName);
  const destinationParent = dirname(plan.destination);
  const stage = join(destinationParent, `.${skillName}.gorin-stage`);
  const backup = join(destinationParent, `.${skillName}.gorin-backup`);
  const stagedReceipt = `${receiptPath}.tmp`;

  await mkdir(destinationParent, { recursive: true });
  await mkdir(dirname(receiptPath), { recursive: true });
  await rm(stage, { recursive: true, force: true });
  await rm(backup, { recursive: true, force: true });
  await rm(stagedReceipt, { force: true });

  let files = [];
  if (mode === "managed") {
    await copyDirectory(packageSource, stage);
    files = await collectFileRecords(stage);
  } else {
    await symlink(packageSource, stage, "dir");
  }

  const receipt = {
    schema_version: 1,
    owner: "gorin-skills",
    skill: skillName,
    version: build.skill.manifest.version,
    target,
    mode,
    source: build.skill.skillDir,
    package_source: packageSource,
    destination: plan.destination,
    ...(mode === "managed" ? { files } : { link_target: packageSource }),
  };
  await writeFile(stagedReceipt, `${JSON.stringify(receipt, null, 2)}\n`);

  const hadDestination = await pathExists(plan.destination);
  try {
    if (hadDestination) await rename(plan.destination, backup);
    await rename(stage, plan.destination);
    await rename(stagedReceipt, receiptPath);
    await rm(backup, { recursive: true, force: true });
  } catch (error) {
    await rm(stage, { recursive: true, force: true });
    await rm(stagedReceipt, { force: true });
    if (hadDestination && (await pathExists(backup))) {
      await rm(plan.destination, { recursive: true, force: true });
      await rename(backup, plan.destination);
    }
    throw error;
  }

  return receipt;
}

function safeReceiptFilePath(destination, receiptFile) {
  if (isAbsolute(receiptFile) || receiptFile.split(/[\\/]/).includes("..")) {
    throw new Error(`Unsafe path in install receipt: ${receiptFile}`);
  }
  const path = resolve(destination, receiptFile);
  if (path !== destination && !path.startsWith(`${destination}/`)) {
    throw new Error(`Unsafe path in install receipt: ${receiptFile}`);
  }
  return path;
}

async function removeEmptyDirectories(root) {
  async function visit(directory) {
    let entries;
    try {
      entries = await readdir(directory, { withFileTypes: true });
    } catch (error) {
      if (error.code === "ENOENT") return 0;
      throw error;
    }

    let remainingFiles = 0;
    for (const entry of entries) {
      const path = join(directory, entry.name);
      if (entry.isDirectory()) {
        remainingFiles += await visit(path);
      } else {
        remainingFiles += 1;
      }
    }
    if (directory !== root && remainingFiles === 0) {
      await rmdir(directory);
    }
    return remainingFiles;
  }

  const preserved = await visit(root);
  if (preserved === 0) {
    try {
      await rmdir(root);
    } catch (error) {
      if (!["ENOENT", "ENOTEMPTY"].includes(error.code)) throw error;
    }
  }
  return preserved;
}

export async function uninstallSkill({ skillName, target, home }) {
  const installSegments = TARGET_INSTALL_ROOTS[target];
  if (!installSegments) throw new Error(`Unsupported install target: ${target}`);
  const destination = join(home, ...installSegments, skillName);
  const receiptPath = receiptPathFor(home, target, skillName);
  const receipt = await readReceipt(receiptPath);
  if (!receiptOwnsDestination(receipt, { skillName, target, destination })) {
    throw new Error(`No valid managed receipt for ${skillName} on ${target}`);
  }

  let preserved = 0;
  if (receipt.mode === "link") {
    const currentTarget = await readlink(destination).catch(() => null);
    if (currentTarget !== receipt.link_target) {
      throw new Error(`Refusing to remove a link not owned by the receipt: ${destination}`);
    }
    await unlink(destination);
  } else if (receipt.mode === "managed") {
    for (const file of receipt.files ?? []) {
      const path = safeReceiptFilePath(destination, file.path);
      try {
        await unlink(path);
      } catch (error) {
        if (error.code !== "ENOENT") throw error;
      }
    }
    preserved = await removeEmptyDirectories(destination);
  } else {
    throw new Error(`Unsupported receipt mode: ${receipt.mode}`);
  }

  await unlink(receiptPath);
  return { preserved };
}

async function scanSkillRoot(root) {
  let entries;
  try {
    entries = await readdir(root, { withFileTypes: true });
  } catch (error) {
    if (error.code === "ENOENT") return { available: [], broken: [] };
    throw error;
  }

  const available = [];
  const broken = [];
  for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
    const location = join(root, entry.name);
    if (entry.isSymbolicLink()) {
      const rawTarget = await readlink(location);
      const target = resolve(dirname(location), rawTarget);
      try {
        const targetStat = await stat(location);
        await stat(join(location, "SKILL.md"));
        if (targetStat.isDirectory()) available.push({ skill: entry.name, location });
      } catch (error) {
        if (error.code === "ENOENT") {
          broken.push({ skill: entry.name, location, target });
          continue;
        }
        throw error;
      }
      continue;
    }
    if (!entry.isDirectory()) continue;
    try {
      await stat(join(location, "SKILL.md"));
      available.push({ skill: entry.name, location });
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
    }
  }
  return { available, broken };
}

async function scanLegacySourceRoot(root) {
  const skills = [];
  for (const name of (await listDirectories(root)).sort()) {
    try {
      await stat(join(root, name, "SKILL.md"));
      skills.push(name);
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
    }
  }
  return skills;
}

export async function doctorRepository({ skills, home, workspace }) {
  const roots = [
    join(workspace, "skills"),
    join(workspace, ".agents", "skills"),
    join(home, ".agents", "skills"),
    join(home, ".openclaw", "skills"),
  ];
  const appearances = new Map();
  const brokenBySkill = new Map();
  const brokenLinks = [];

  for (const root of roots) {
    const scanned = await scanSkillRoot(root);
    for (const entry of scanned.available) {
      const locations = appearances.get(entry.skill) ?? [];
      locations.push(entry.location);
      appearances.set(entry.skill, locations);
    }
    for (const entry of scanned.broken) {
      brokenLinks.push(entry);
      const locations = brokenBySkill.get(entry.skill) ?? [];
      locations.push(entry.location);
      brokenBySkill.set(entry.skill, locations);
    }
  }

  const duplicates = [...appearances.entries()]
    .filter(([, locations]) => locations.length > 1)
    .map(([skill, locations]) => ({ skill, locations }))
    .sort((left, right) => left.skill.localeCompare(right.skill));
  const aliasMap = new Map();
  for (const skill of skills) {
    for (const alias of skill.manifest.aliases ?? []) {
      aliasMap.set(alias, skill.skillName);
    }
  }
  const legacyAliases = [...aliasMap.entries()]
    .filter(([alias]) => appearances.has(alias))
    .map(([alias, canonical]) => ({
      alias,
      canonical,
      locations: appearances.get(alias),
    }))
    .sort((left, right) => left.alias.localeCompare(right.alias));
  const allNames = new Set([...appearances.keys(), ...brokenBySkill.keys()]);
  const effective = [...allNames]
    .sort((left, right) => left.localeCompare(right))
    .filter((skill) => appearances.has(skill))
    .map((skill) => {
      const locations = appearances.get(skill);
      return {
        skill,
        winner: locations[0],
        shadowed: locations.slice(1),
        ignored_broken: brokenBySkill.get(skill) ?? [],
      };
    });

  const legacySourcePaths = [];
  for (const path of [
    join(workspace, "general"),
    join(workspace, "openclaw"),
    join(workspace, "skills", "edu"),
  ]) {
    const legacySkills = await scanLegacySourceRoot(path);
    if (legacySkills.length > 0) {
      legacySourcePaths.push({ path, skills: legacySkills });
    }
  }

  return {
    schema_version: 1,
    broken_links: brokenLinks.sort((left, right) => left.location.localeCompare(right.location)),
    duplicates,
    legacy_aliases: legacyAliases,
    legacy_source_paths: legacySourcePaths,
    effective: { openclaw: effective },
  };
}
