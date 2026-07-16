#!/usr/bin/env node

import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { parse } from "yaml";
import {
  applyRelease,
  computeReleasePlan,
  verifyRelease,
} from "../src/release.mjs";
import { buildInventory, renderLegacyProfile } from "../src/inventory.mjs";
import { migrateDomain } from "../src/migrate.mjs";
import {
  buildCatalog,
  buildSkillPackages,
  computeContentDigest,
  createInstallPlan,
  doctorRepository,
  installSkill,
  loadExternalSources,
  qualifySkill,
  renderDocumentationIndex,
  resolveProfile,
  uninstallSkill,
  validateRepository,
  validateLifecycleTransitions,
} from "../src/governance.mjs";

function readOption(args, name, fallback) {
  const index = args.indexOf(name);
  if (index === -1) return fallback;
  if (!args[index + 1]) throw new Error(`${name} requires a value`);
  return args[index + 1];
}

function requireOption(args, name) {
  const value = readOption(args, name);
  if (!value) throw new Error(`${name} is required`);
  return value;
}

async function readWorkingCatalogVersion(root) {
  try {
    const release = parse(
      await readFile(resolve(root, "release", "repository.yaml"), "utf8"),
    );
    if (release?.version) return release.version;
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
  try {
    const packageMetadata = JSON.parse(
      await readFile(resolve(root, "package.json"), "utf8"),
    );
    return packageMetadata?.version;
  } catch (error) {
    if (error.code === "ENOENT") return undefined;
    throw error;
  }
}

async function main() {
  const [, , command, ...args] = process.argv;
  const root = resolve(readOption(args, "--root", process.cwd()));

  if (command === "validate") {
    const skills = await validateRepository(root);
    const externalSources = await loadExternalSources(root);
    buildCatalog(skills, externalSources);
    const baselinePath = readOption(args, "--baseline");
    if (baselinePath) {
      const baseline = JSON.parse(await readFile(resolve(baselinePath), "utf8"));
      validateLifecycleTransitions(skills, baseline);
    }
    process.stdout.write(`Validated ${skills.length} skill${skills.length === 1 ? "" : "s"}\n`);
    return;
  }

  if (command === "catalog") {
    const output = resolve(
      readOption(args, "--output", resolve(root, "catalog", "index.json")),
    );
    const skills = await validateRepository(root);
    const externalSources = await loadExternalSources(root);
    const catalog = buildCatalog(
      skills,
      externalSources,
      await readWorkingCatalogVersion(root),
    );
    await mkdir(dirname(output), { recursive: true });
    await writeFile(output, `${JSON.stringify(catalog, null, 2)}\n`);
    process.stdout.write(`Wrote catalog with ${catalog.skills.length} entries to ${output}\n`);
    return;
  }

  if (command === "digest") {
    const path = resolve(requireOption(args, "--path"));
    process.stdout.write(`${await computeContentDigest(path)}\n`);
    return;
  }

  if (command === "build") {
    const output = resolve(readOption(args, "--output", resolve(root, "dist")));
    const skills = await validateRepository(root);
    if (args.includes("--all")) {
      for (const skill of skills) {
        await buildSkillPackages(skills, skill.skillName, output);
      }
      process.stdout.write(`Built ${skills.length} skills for all declared targets\n`);
      return;
    }
    const skillName = requireOption(args, "--skill");
    const result = await buildSkillPackages(skills, skillName, output);
    process.stdout.write(
      `Built ${skillName} for ${result.targets.length} targets\n`,
    );
    return;
  }

  if (command === "qualify") {
    const skillName = requireOption(args, "--skill");
    const skills = await validateRepository(root);
    const report = await qualifySkill({ root, skills, skillName });
    process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
    return;
  }

  if (command === "docs") {
    const output = resolve(
      readOption(args, "--output", resolve(root, "docs", "skills", "index.md")),
    );
    const skills = await validateRepository(root);
    const externalSources = await loadExternalSources(root);
    await mkdir(dirname(output), { recursive: true });
    await writeFile(output, renderDocumentationIndex(skills, externalSources));
    process.stdout.write(`Wrote documentation index with ${skills.length} local skills\n`);
    return;
  }

  if (command === "scaffold") {
    const name = requireOption(args, "--name");
    const domain = requireOption(args, "--domain");
    const description = requireOption(args, "--description");
    const domains = new Set([
      "education",
      "content",
      "documents",
      "knowledge",
      "research",
      "agent-ops",
      "engineering",
    ]);
    if (!domains.has(domain)) throw new Error(`Unsupported domain: ${domain}`);
    if (!/^gorin-[a-z0-9-]+$/.test(name)) {
      throw new Error("First-party scaffold names must use gorin- and lowercase kebab-case");
    }
    const directory = resolve(root, "skills", domain, name);
    await mkdir(directory, { recursive: false });
    await writeFile(
      resolve(directory, "SKILL.md"),
      `---\nname: ${name}\ndescription: ${JSON.stringify(description)}\nlicense: MIT\n---\n\n# ${name}\n\nDefine the bounded workflow and completion criteria here.\n`,
    );
    await writeFile(
      resolve(directory, "manifest.yaml"),
      `schema_version: 1\nversion: 0.1.0\ndomain: ${domain}\nlifecycle: incubating\nownership: first-party\naudience: public\ntargets:\n  - agent-skills\n  - codex\n  - claude-code\n  - openclaw\n`,
    );
    process.stdout.write(`Scaffolded ${name} in skills/${domain}/${name}\n`);
    return;
  }

  if (command === "install") {
    const skillName = requireOption(args, "--skill");
    const target = requireOption(args, "--target");
    const home = resolve(requireOption(args, "--home"));
    const skills = await validateRepository(root);
    if (args.includes("--dry-run")) {
      const plan = await createInstallPlan({ skills, skillName, target, root, home });
      process.stdout.write(`${JSON.stringify(plan, null, 2)}\n`);
      return;
    }
    const mode = readOption(args, "--mode", "managed");
    const receipt = await installSkill({ skills, skillName, target, root, home, mode });
    process.stdout.write(
      `Installed ${skillName} ${receipt.version} for ${target} (${mode})\n`,
    );
    return;
  }

  if (command === "uninstall") {
    const skillName = requireOption(args, "--skill");
    const target = requireOption(args, "--target");
    const home = resolve(requireOption(args, "--home"));
    const result = await uninstallSkill({ skillName, target, home });
    process.stdout.write(
      `Uninstalled ${skillName} from ${target}; preserved ${result.preserved} unowned file${result.preserved === 1 ? "" : "s"}\n`,
    );
    return;
  }

  if (command === "doctor") {
    const home = resolve(requireOption(args, "--home"));
    const workspace = resolve(readOption(args, "--workspace", root));
    const skills = await validateRepository(root);
    const report = await doctorRepository({ skills, home, workspace });
    process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
    return;
  }

  if (command === "profile") {
    const name = requireOption(args, "--name");
    const skills = await validateRepository(root);
    const profile = await resolveProfile(root, skills, name);
    process.stdout.write(`${JSON.stringify(profile, null, 2)}\n`);
    return;
  }

  if (command === "release") {
    const computed = await computeReleasePlan(root);
    if (args.includes("--dry-run")) {
      const plan = await verifyRelease(root, computed);
      process.stdout.write(`${JSON.stringify(plan, null, 2)}\n`);
      return;
    }
    const plan = await applyRelease(root, computed);
    process.stdout.write(
      `Released repository ${plan.repository.to} with ${plan.skills.length} skill update${plan.skills.length === 1 ? "" : "s"}\n`,
    );
    return;
  }

  if (command === "inventory") {
    const output = resolve(
      readOption(args, "--output", resolve(root, "inventory", "skills.json")),
    );
    const legacyProfile = resolve(
      readOption(
        args,
        "--legacy-profile",
        resolve(root, "profiles", "legacy-v1.yaml"),
      ),
    );
    const inventory = await buildInventory(root);
    await mkdir(dirname(output), { recursive: true });
    await writeFile(output, `${JSON.stringify(inventory, null, 2)}\n`);
    const inventoryReference = output.startsWith(`${root}/`)
      ? output.slice(root.length + 1)
      : output;
    await mkdir(dirname(legacyProfile), { recursive: true });
    await writeFile(
      legacyProfile,
      renderLegacyProfile(inventory, inventoryReference),
    );
    process.stdout.write(
      `Inventoried ${inventory.summary.local_skills} local skills (${inventory.summary.legacy_v1} legacy-v1, ${inventory.summary.v2} v2)\n`,
    );
    return;
  }

  if (command === "migrate") {
    const domain = requireOption(args, "--domain");
    const inventory = resolve(
      readOption(args, "--inventory", resolve(root, "inventory", "skills.json")),
    );
    const count = await migrateDomain(root, inventory, domain);
    process.stdout.write(
      `Migrated ${count} legacy skill${count === 1 ? "" : "s"} into ${domain}\n`,
    );
    return;
  }

  throw new Error(`Unknown command: ${command ?? "(missing)"}`);
}

main().catch((error) => {
  process.stderr.write(`error: ${error.message}\n`);
  process.exitCode = 1;
});
