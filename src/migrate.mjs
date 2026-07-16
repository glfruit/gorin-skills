import { mkdir, readFile, rename, rm, writeFile } from "node:fs/promises";
import { dirname, isAbsolute, join, resolve } from "node:path";
import { parse, stringify } from "yaml";

function parseLegacySkill(source, fallbackName) {
  const match = source.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)([\s\S]*)$/);
  if (!match) throw new Error(`${fallbackName}: legacy SKILL.md has no frontmatter`);
  let frontmatter;
  try {
    frontmatter = parse(match[1]) ?? {};
  } catch {
    const rawDescription = match[1].match(/^description:\s*(.*)$/m)?.[1]?.trim();
    frontmatter = {
      name: match[1].match(/^name:\s*([^\r\n]+)$/m)?.[1]?.trim() ?? fallbackName,
      description: rawDescription?.replace(/^(["'])(.*)\1$/, "$2"),
      version: match[1].match(/^version:\s*([^\r\n]+)$/m)?.[1]?.trim(),
    };
  }
  if (!frontmatter.description) {
    throw new Error(`${fallbackName}: legacy SKILL.md requires a description`);
  }
  return { frontmatter, body: match[2] };
}

function normalizeVersion(value) {
  const version = String(value ?? "0.1.0").trim();
  if (/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/.test(version)) {
    return version;
  }
  if (/^\d+\.\d+$/.test(version)) return `${version}.0`;
  return "0.1.0";
}

function buildAdapter(frontmatter) {
  const legacyOpenClaw =
    frontmatter.metadata?.openclaw && typeof frontmatter.metadata.openclaw === "object"
      ? { ...frontmatter.metadata.openclaw }
      : {};
  const homepage = frontmatter.homepage ?? legacyOpenClaw.homepage;
  delete legacyOpenClaw.homepage;
  if (frontmatter.requires && !legacyOpenClaw.requires) {
    legacyOpenClaw.requires = frontmatter.requires;
  }
  const adapter = {
    ...(homepage ? { homepage } : {}),
    ...(typeof frontmatter["user-invocable"] === "boolean"
      ? { user_invocable: frontmatter["user-invocable"] }
      : {}),
    ...(typeof frontmatter["disable-model-invocation"] === "boolean"
      ? { disable_model_invocation: frontmatter["disable-model-invocation"] }
      : {}),
    ...(frontmatter["command-dispatch"]
      ? { command_dispatch: frontmatter["command-dispatch"] }
      : {}),
    ...(frontmatter["command-tool"] ? { command_tool: frontmatter["command-tool"] } : {}),
    ...(frontmatter["command-arg-mode"]
      ? { command_arg_mode: frontmatter["command-arg-mode"] }
      : {}),
    ...(Object.keys(legacyOpenClaw).length > 0 ? { metadata: legacyOpenClaw } : {}),
  };
  return Object.keys(adapter).length > 0 ? adapter : null;
}

function renderStandardSkill(name, frontmatter, body) {
  const standard = {
    name,
    description: frontmatter.description,
    license: frontmatter.license ?? "MIT",
    ...(frontmatter.compatibility ? { compatibility: frontmatter.compatibility } : {}),
  };
  return `---\n${stringify(standard).trimEnd()}\n---\n${body}`;
}

function safeRepositoryPath(root, repositoryPath, label) {
  if (
    typeof repositoryPath !== "string" ||
    isAbsolute(repositoryPath) ||
    repositoryPath.split(/[\\/]/).includes("..")
  ) {
    throw new Error(`${label}: unsafe repository path`);
  }
  const path = resolve(root, repositoryPath);
  if (path !== root && !path.startsWith(`${root}/`)) {
    throw new Error(`${label}: repository path escapes root`);
  }
  return path;
}

async function pathExists(path) {
  try {
    await readFile(path);
    return true;
  } catch (error) {
    if (error.code === "EISDIR") return true;
    if (error.code === "ENOENT") return false;
    throw error;
  }
}

async function migrateEntry(root, entry) {
  const sourceDir = safeRepositoryPath(root, entry.path, entry.id);
  const targetDir = safeRepositoryPath(root, entry.migration.target, entry.id);
  if (await pathExists(targetDir)) {
    throw new Error(`${entry.id}: migration target already exists: ${entry.migration.target}`);
  }
  await mkdir(dirname(targetDir), { recursive: true });
  await rename(sourceDir, targetDir);

  const skillPath = join(targetDir, "SKILL.md");
  const metaPath = join(targetDir, ".skill-meta.json");
  const originalSkill = await readFile(skillPath, "utf8");
  let originalMeta = null;
  try {
    originalMeta = await readFile(metaPath, "utf8");
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }

  try {
    const { frontmatter, body } = parseLegacySkill(originalSkill, entry.id);
    const metadata = originalMeta ? JSON.parse(originalMeta) : {};
    const targetName = entry.migration.target.split("/").at(-1);
    const adapter = buildAdapter(frontmatter);
    const manifest = {
      schema_version: 1,
      version: normalizeVersion(frontmatter.version ?? metadata.version),
      domain: entry.domain,
      lifecycle: entry.lifecycle,
      ownership: "first-party",
      audience: "public",
      targets: ["agent-skills", "codex", "claude-code", "openclaw"],
      ...(targetName !== entry.id ? { aliases: [entry.id] } : {}),
      ...(adapter ? { adapters: { openclaw: adapter } } : {}),
    };
    await writeFile(skillPath, renderStandardSkill(targetName, frontmatter, body));
    await writeFile(join(targetDir, "manifest.yaml"), stringify(manifest));
    await rm(metaPath, { force: true });
  } catch (error) {
    await rm(join(targetDir, "manifest.yaml"), { force: true });
    await writeFile(skillPath, originalSkill);
    if (originalMeta !== null) await writeFile(metaPath, originalMeta);
    await rename(targetDir, sourceDir);
    throw error;
  }
}

export async function migrateDomain(root, inventoryPath, domain) {
  const inventory = JSON.parse(await readFile(inventoryPath, "utf8"));
  if (inventory?.schema_version !== 1 || !Array.isArray(inventory.skills)) {
    throw new Error("Invalid migration inventory");
  }
  const entries = inventory.skills.filter(
    (entry) =>
      entry.representation === "legacy-v1" &&
      entry.distributable_legacy &&
      entry.domain === domain &&
      entry.migration?.disposition === "requalify",
  );
  for (const entry of entries) await migrateEntry(root, entry);
  return entries.length;
}
