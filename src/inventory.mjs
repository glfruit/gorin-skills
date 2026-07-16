import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { lstat, readFile, readdir, stat } from "node:fs/promises";
import { extname, join, relative } from "node:path";
import { parse } from "yaml";
import { loadExternalSources, validateRepository } from "./governance.mjs";

const execFileAsync = promisify(execFile);
const MANAGED_MIRROR_NAMES = new Set([
  "docx",
  "pdf",
  "xlsx",
  "obsidian-bases",
  "obsidian-canvas",
  "obsidian-cli",
  "obsidian-defuddle",
  "obsidian-md",
]);
const ADAPTED_FIRST_PARTY_NAMES = new Set(["md2pdf"]);
const RESTRICTED_NAMES = new Set(["docx", "pdf", "xlsx"]);
const DEPRECATED_NAMES = new Set([
  "ai-builder-digest",
  "baoyu-xhs-images",
  "zk-literature",
]);
const DOCUMENT_SKILLS = new Set(["docx", "pdf", "xlsx", "md2pdf", "superdoc"]);
const EDUCATION_SKILLS = new Set(["openmaic"]);
const RESEARCH_SKILLS = new Set([
  "ai-builder-digest",
  "ai-image-digest",
  "autoresearch",
  "download-anything",
  "zk-literature",
]);
const AGENT_OPS_SKILLS = new Set([
  "agent-team-composer",
  "harness-audit",
  "log-watchdog",
  "oc-card",
  "plugin-updater",
  "safe-mode",
  "teambook",
]);
const CONTENT_SKILLS = new Set([
  "bearclaw-native",
  "visual-knowledge-explainer",
]);
const SAFE_TEXT_EXTENSIONS = new Set([
  ".md",
  ".txt",
  ".py",
  ".js",
  ".mjs",
  ".cjs",
  ".ts",
  ".tsx",
  ".sh",
  ".json",
  ".yaml",
  ".yml",
  ".toml",
]);
const SCAN_SKIP_SEGMENTS = new Set(["vendor", "node_modules", ".venv", "venv"]);
const RUNTIME_SEGMENTS = new Set([
  "out",
  "output",
  "outputs",
  ".cache",
  "cache",
  "tmp",
  "temp",
  "results",
  "generated",
]);
const INSTALL_ROOTS = [
  "~/.gorin-skills",
  "~/.openclaw/skills",
  "~/.agents/skills",
  "~/.claude/skills",
  "~/.codex/skills",
];

async function pathExists(path) {
  try {
    await lstat(path);
    return true;
  } catch (error) {
    if (error.code === "ENOENT") return false;
    throw error;
  }
}

async function directSkillDirectories(root) {
  let entries;
  try {
    entries = await readdir(root, { withFileTypes: true });
  } catch (error) {
    if (error.code === "ENOENT") return [];
    throw error;
  }
  const directories = [];
  for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
    if (!entry.isDirectory() || entry.name.startsWith(".")) continue;
    const directory = join(root, entry.name);
    if (await pathExists(join(directory, "SKILL.md"))) {
      directories.push({ name: entry.name, directory });
    }
  }
  return directories;
}

function parseFrontmatter(source) {
  const match = source.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);
  if (!match) return {};
  try {
    return parse(match[1]) ?? {};
  } catch {
    const description = match[1].match(/^description:\s*(.*)$/m)?.[1]?.trim();
    const version = match[1].match(/^version:\s*([^\r\n]+)$/m)?.[1]?.trim();
    return {
      ...(description ? { description } : {}),
      ...(version ? { version } : {}),
      __frontmatter_status: "invalid-yaml",
    };
  }
}

function sourceClassification(name, repositoryPath, metadata) {
  if (repositoryPath.startsWith("skills/edu/") && name.startsWith("gorin-")) {
    return {
      sourceType: "first-party",
      basis: "legacy gorin namespace under the first-party education root",
    };
  }
  const origin = String(metadata?.origin ?? "").toLowerCase();
  const author = String(metadata?.author ?? "").toLowerCase();
  if (origin.includes("adapted") || ADAPTED_FIRST_PARTY_NAMES.has(name)) {
    return {
      sourceType: "adapted-first-party",
      basis: ".skill-meta.json or known legacy metadata declares an adaptation",
    };
  }
  if (
    origin === "self" ||
    origin.startsWith("enhanced-skill-creator") ||
    origin.startsWith("daily-") ||
    ["gorin", "devops"].includes(author)
  ) {
    return {
      sourceType: "first-party",
      basis: ".skill-meta.json explicitly attributes the skill to this repository",
    };
  }
  return {
    sourceType: "managed-mirror",
    basis:
      name.startsWith("baoyu-") || MANAGED_MIRROR_NAMES.has(name)
        ? "known third-party family"
        : "conservative fallback: no first-party provenance evidence",
  };
}

function domainFor(name, repositoryPath) {
  if (repositoryPath.startsWith("skills/edu/")) return "education";
  if (DOCUMENT_SKILLS.has(name)) return "documents";
  if (EDUCATION_SKILLS.has(name)) return "education";
  if (RESEARCH_SKILLS.has(name)) return "research";
  if (AGENT_OPS_SKILLS.has(name)) return "agent-ops";
  if (name.startsWith("baoyu-") || CONTENT_SKILLS.has(name)) return "content";
  if (
    /^(?:atlas-|idea-|neobear|obsidian-|outline$|pkm-|voice-to-zettel|web-reader|zk-router)/.test(
      name,
    )
  ) {
    return "knowledge";
  }
  return "engineering";
}

function licenseFor(sourceType, name, directory, rootLicenseExists) {
  if (sourceType === "first-party") {
    return rootLicenseExists
      ? { status: "resolved", evidence: "LICENSE" }
      : { status: "unresolved", evidence: null };
  }
  if (sourceType === "adapted-first-party") {
    return {
      status: "unresolved",
      evidence: "upstream license/attribution is not bundled with the adaptation",
    };
  }
  if (RESTRICTED_NAMES.has(name)) {
    return {
      status: "restricted",
      evidence: `${relative(process.cwd(), directory)}/LICENSE.txt`,
    };
  }
  return {
    status: "unresolved",
    evidence: "upstream revision, digest, and distributable license chain are incomplete",
  };
}

async function trackedFiles(root, repositoryPath) {
  try {
    const { stdout } = await execFileAsync(
      "git",
      ["ls-files", "-z", "--", repositoryPath],
      { cwd: root, encoding: "utf8", maxBuffer: 16 * 1024 * 1024 },
    );
    return stdout.split("\0").filter(Boolean).sort();
  } catch {
    return [];
  }
}

function secretShaped(relativePath) {
  const name = relativePath.split("/").at(-1);
  return (
    (/^\.env(?:\.|$)/.test(name) && name !== ".env.example") ||
    /\.(?:pem|key|p12|pfx)$/i.test(name) ||
    /^(?:id_rsa|id_ed25519)(?:\.|$)/.test(name)
  );
}

async function findingsFor(root, repositoryPath) {
  const files = await trackedFiles(root, repositoryPath);
  const personal = new Set();
  const runtime = new Set();
  const roots = new Map(INSTALL_ROOTS.map((installRoot) => [installRoot, new Set()]));
  for (const trackedPath of files) {
    const insidePath = trackedPath.slice(repositoryPath.length + 1);
    const segments = insidePath.split("/");
    if (segments.some((segment) => RUNTIME_SEGMENTS.has(segment))) {
      runtime.add(insidePath);
    }
    if (
      secretShaped(insidePath) ||
      segments.some((segment) => SCAN_SKIP_SEGMENTS.has(segment)) ||
      !SAFE_TEXT_EXTENSIONS.has(extname(insidePath).toLowerCase())
    ) {
      continue;
    }
    const fullPath = join(root, trackedPath);
    let fileStat;
    try {
      fileStat = await stat(fullPath);
    } catch (error) {
      if (error.code === "ENOENT") continue;
      throw error;
    }
    if (fileStat.size > 1024 * 1024) continue;
    const source = await readFile(fullPath, "utf8");
    if (/\/(?:Users|home)\/[A-Za-z0-9._-]+\//.test(source)) personal.add(insidePath);
    for (const installRoot of INSTALL_ROOTS) {
      if (source.includes(installRoot)) roots.get(installRoot).add(insidePath);
    }
  }
  return {
    personal_absolute_paths: [...personal].sort(),
    hard_coded_install_roots: [...roots.entries()]
      .filter(([, paths]) => paths.size > 0)
      .map(([installRoot, paths]) => ({ root: installRoot, files: [...paths].sort() })),
    tracked_runtime_artifacts: [...runtime].sort(),
  };
}

function migrationFor(sourceType, name, domain) {
  if (sourceType === "first-party") {
    return {
      disposition: "requalify",
      target: `skills/${domain}/${name.startsWith("gorin-") ? name : `gorin-${name}`}`,
    };
  }
  if (sourceType === "adapted-first-party") {
    return {
      disposition: "rebuild-adaptation",
      target: `skills/${domain}/gorin-${name}`,
    };
  }
  if (RESTRICTED_NAMES.has(name)) {
    return { disposition: "retire-local-copy", target: null };
  }
  return { disposition: "externalize-or-pin", target: null };
}

async function legacyEntry(root, item, repositoryPath, rootLicenseExists) {
  const skillSource = await readFile(join(item.directory, "SKILL.md"), "utf8");
  const frontmatter = parseFrontmatter(skillSource);
  let metadata = {};
  try {
    metadata = JSON.parse(await readFile(join(item.directory, ".skill-meta.json"), "utf8"));
  } catch (error) {
    if (error.code !== "ENOENT" && !(error instanceof SyntaxError)) throw error;
  }
  const classification = sourceClassification(item.name, repositoryPath, metadata);
  const sourceType = classification.sourceType;
  const domain = domainFor(item.name, repositoryPath);
  const license = licenseFor(sourceType, item.name, item.directory, rootLicenseExists);
  const lifecycle =
    DEPRECATED_NAMES.has(item.name) || /\bdeprecated\b/i.test(frontmatter.description ?? "")
      ? "deprecated"
      : "incubating";
  const distributable = sourceType === "first-party" && license.status === "resolved";
  return {
    id: item.name,
    version: typeof frontmatter.version === "string" ? frontmatter.version : "0.0.0-legacy",
    path: repositoryPath,
    representation: "legacy-v1",
    domain,
    lifecycle,
    ownership: sourceType === "managed-mirror" ? "managed-mirror" : "first-party",
    source_type: sourceType,
    classification_basis: classification.basis,
    frontmatter_status: frontmatter.__frontmatter_status ?? "valid",
    license,
    distributable_legacy: distributable,
    migration: migrationFor(sourceType, item.name, domain),
    findings: await findingsFor(root, repositoryPath),
  };
}

export async function buildInventory(root) {
  const [v2Skills, externalSources, openclawLegacy, educationLegacy] = await Promise.all([
    validateRepository(root),
    loadExternalSources(root),
    directSkillDirectories(join(root, "openclaw")),
    directSkillDirectories(join(root, "skills", "edu")),
  ]);
  const rootLicenseExists = await pathExists(join(root, "LICENSE"));
  const entries = [];
  for (const skill of v2Skills) {
    entries.push({
      id: skill.skillName,
      version: skill.manifest.version,
      path: `skills/${skill.domain}/${skill.skillName}`,
      representation: "v2",
      domain: skill.domain,
      lifecycle: skill.manifest.lifecycle,
      ownership: skill.manifest.ownership,
      source_type:
        skill.manifest.provenance?.kind === "adapted"
          ? "adapted-first-party"
          : skill.manifest.ownership,
      aliases: skill.manifest.aliases ?? [],
      license: {
        status: (await pathExists(join(skill.skillDir, "LICENSE"))) || rootLicenseExists
          ? "resolved"
          : "unresolved",
        evidence: (await pathExists(join(skill.skillDir, "LICENSE")))
          ? `skills/${skill.domain}/${skill.skillName}/LICENSE`
          : rootLicenseExists
            ? "LICENSE"
            : null,
      },
      distributable_legacy: false,
      migration: { disposition: "complete", target: null },
      findings: await findingsFor(root, `skills/${skill.domain}/${skill.skillName}`),
    });
  }
  for (const item of openclawLegacy) {
    entries.push(
      await legacyEntry(
        root,
        item,
        `openclaw/${item.name}`,
        rootLicenseExists,
      ),
    );
  }
  for (const item of educationLegacy) {
    entries.push(
      await legacyEntry(
        root,
        item,
        `skills/edu/${item.name}`,
        rootLicenseExists,
      ),
    );
  }
  entries.sort((left, right) => left.path.localeCompare(right.path));
  const paths = new Set(entries.map((entry) => entry.path));
  if (paths.size !== entries.length) throw new Error("Inventory discovered duplicate skill paths");
  const legacy = entries.filter((entry) => entry.representation === "legacy-v1");
  const distributableLegacy = legacy.filter((entry) => entry.distributable_legacy);
  return {
    schema_version: 1,
    summary: {
      local_skills: entries.length,
      legacy_v1: legacy.length,
      v2: entries.length - legacy.length,
      distributable_legacy: distributableLegacy.length,
      external_sources: externalSources.length,
    },
    external_sources: externalSources.map((source) => ({
      id: source.id,
      ownership: "external",
      source: source.source,
    })),
    skills: entries,
  };
}

export function renderLegacyProfile(inventory, inventoryPath = "inventory/skills.json") {
  const ids = inventory.skills
    .filter((skill) => skill.representation === "legacy-v1" && skill.distributable_legacy)
    .map((skill) => skill.id)
    .sort();
  if (ids.length === 0) {
    const v2Entries = inventory.skills.filter(
      (skill) => skill.representation === "v2" && skill.lifecycle !== "retired",
    );
    const v2Skills = v2Entries.map((skill) => skill.id).sort();
    const lifecycles = [...new Set(v2Entries.map((skill) => skill.lifecycle))].sort();
    return [
      "schema_version: 1",
      "name: legacy-v1",
      "description: Explicit one-major compatibility profile using canonical v2 sources and generated aliases.",
      "end_of_support: before-repository-major-3",
      "compatibility_aliases: true",
      "skills:",
      ...v2Skills.map((id) => `  - ${id}`),
      "allow_lifecycles:",
      ...lifecycles.map((lifecycle) => `  - ${lifecycle}`),
      "",
    ].join("\n");
  }
  return [
    "schema_version: 1",
    "name: legacy-v1",
    "description: Explicit one-major compatibility profile for legally distributable v1 skills.",
    "legacy:",
    `  inventory: ${inventoryPath}`,
    "  end_of_support: before-repository-major-3",
    "  skills:",
    ...ids.map((id) => `    - ${id}`),
    "",
  ].join("\n");
}
