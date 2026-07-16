import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import {
  existsSync,
  lstatSync,
  mkdtempSync,
  mkdirSync,
  readlinkSync,
  readdirSync,
  readFileSync,
  rmSync,
  statSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const projectRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const cliPath = join(projectRoot, "scripts", "gorin-skills.mjs");

function createRepositoryFixture() {
  const root = mkdtempSync(join(tmpdir(), "gorin-skills-test-"));
  const skillDir = join(
    root,
    "skills",
    "education",
    "gorin-lesson-review",
  );
  mkdirSync(skillDir, { recursive: true });
  writeFileSync(
    join(skillDir, "SKILL.md"),
    [
      "---",
      "name: gorin-lesson-review",
      "description: Review a lesson against its approved teaching outline.",
      "---",
      "",
      "# Lesson Review",
      "",
      "Review the supplied lesson and report outline gaps.",
      "",
    ].join("\n"),
  );
  writeFileSync(
    join(skillDir, "manifest.yaml"),
    [
      "schema_version: 1",
      "version: 0.1.0",
      "domain: education",
      "lifecycle: incubating",
      "ownership: first-party",
      "audience: public",
      "targets:",
      "  - agent-skills",
      "",
    ].join("\n"),
  );
  return root;
}

function snapshotTree(root) {
  const files = [];

  function visit(directory, prefix = "") {
    for (const name of readdirSync(directory).sort()) {
      const path = join(directory, name);
      const relativePath = join(prefix, name);
      if (statSync(path).isDirectory()) {
        visit(path, relativePath);
      } else {
        files.push([relativePath, readFileSync(path, "utf8")]);
      }
    }
  }

  visit(root);
  return files;
}

function addSkillFixture(root, { domain, name, lifecycle, version = "0.1.0" }) {
  const skillDir = join(root, "skills", domain, name);
  mkdirSync(skillDir, { recursive: true });
  writeFileSync(
    join(skillDir, "SKILL.md"),
    [
      "---",
      `name: ${name}`,
      `description: Fixture instructions for ${name}.`,
      "---",
      "",
      `# ${name}`,
      "",
    ].join("\n"),
  );
  writeFileSync(
    join(skillDir, "manifest.yaml"),
    [
      "schema_version: 1",
      `version: ${version}`,
      `domain: ${domain}`,
      `lifecycle: ${lifecycle}`,
      "ownership: first-party",
      "audience: public",
      "targets:",
      "  - agent-skills",
      "",
    ].join("\n"),
  );
  if (lifecycle === "candidate") {
    const qualityDir = join(skillDir, "quality");
    mkdirSync(qualityDir);
    writeFileSync(
      join(qualityDir, "evidence.yaml"),
      [
        "schema_version: 1",
        "spec: passed",
        "schema: passed",
        "provenance_and_license: passed",
        "positive_triggers:",
        "  - positive-one",
        "  - positive-two",
        "negative_triggers:",
        "  - negative-one",
        "  - negative-two",
        "golden_cases:",
        "  - golden-one",
        "  - golden-two",
        "tests:",
        "  - command: fixture qualification",
        "    result: passed",
        "target_smoke:",
        "  agent-skills:",
        "    build: passed",
        "    install: passed",
        "runtime_output: clean",
        "",
      ].join("\n"),
    );
    writeFileSync(
      join(qualityDir, "cases.yaml"),
      [
        "schema_version: 1",
        "positive_triggers:",
        "  - id: positive-one",
        `    prompt: Invoke ${name}.`,
        `    expected_route: ${name}`,
        "  - id: positive-two",
        `    prompt: Route this fixture to ${name}.`,
        `    expected_route: ${name}`,
        "negative_triggers:",
        "  - id: negative-one",
        "    prompt: Use another workflow.",
        "    expected_route: not-this-skill",
        "  - id: negative-two",
        "    prompt: Do not use this fixture.",
        "    expected_route: not-this-skill",
        "golden_cases:",
        "  - id: golden-one",
        "    input: First fixture behavior.",
        "    expected_observations: [Observe the first behavior.]",
        "    forbidden_observations: [Invent another behavior.]",
        "  - id: golden-two",
        "    input: Second fixture behavior.",
        "    expected_observations: [Observe the second behavior.]",
        "    forbidden_observations: [Skip the fixture.]",
        "",
      ].join("\n"),
    );
    writeFileSync(
      join(skillDir, "manifest.yaml"),
      `${readFileSync(join(skillDir, "manifest.yaml"), "utf8")}qualification:\n  evidence: quality/evidence.yaml\n`,
    );
  }
  return skillDir;
}

function addPromotionEvidence(root, skillDir, skillName) {
  const manifestPath = join(skillDir, "manifest.yaml");
  writeFileSync(
    manifestPath,
    [
      readFileSync(manifestPath, "utf8").replace(/lifecycle: \w+/, "lifecycle: promoted").trimEnd(),
      "promotion:",
      "  evidence: quality/evidence.yaml",
      `  documentation: docs/skills/${skillName}.md`,
      "  approved_by: fixture-maintainer",
      '  approved_on: "2026-07-14"',
      "  maintenance_commitment: true",
      "",
    ].join("\n"),
  );
  const evidenceDir = join(skillDir, "quality");
  mkdirSync(evidenceDir, { recursive: true });
  writeFileSync(
    join(evidenceDir, "evidence.yaml"),
    [
      "schema_version: 1",
      "spec: passed",
      "schema: passed",
      "provenance_and_license: passed",
      "positive_triggers:",
      "  - fixture positive trigger",
      "negative_triggers:",
      "  - fixture negative trigger",
      "golden_cases:",
      "  - fixture golden behavior",
      "tests:",
      "  - command: npm test",
      "    result: passed",
      "target_smoke:",
      "  agent-skills:",
      "    build: passed",
      "    install: passed",
      "runtime_output: clean",
      "",
    ].join("\n"),
  );
  const docsDir = join(root, "docs", "skills");
  mkdirSync(docsDir, { recursive: true });
  writeFileSync(
    join(docsDir, `${skillName}.md`),
    `# ${skillName}\n\nHuman-facing usage and maintenance notes.\n`,
  );
}

test("validate accepts one valid first-party skill through the CLI", () => {
  const root = createRepositoryFixture();

  const output = execFileSync(process.execPath, [cliPath, "validate", "--root", root], {
    encoding: "utf8",
  });

  assert.equal(output, "Validated 1 skill\n");
});

test("validate rejects a SKILL.md name that differs from its directory", () => {
  const root = createRepositoryFixture();
  const skillDir = join(root, "skills", "education", "gorin-lesson-review");
  writeFileSync(
    join(skillDir, "SKILL.md"),
    [
      "---",
      "name: gorin-other-name",
      "description: Review a lesson against its approved teaching outline.",
      "---",
      "",
      "# Lesson Review",
      "",
    ].join("\n"),
  );

  const result = spawnSync(
    process.execPath,
    [cliPath, "validate", "--root", root],
    { encoding: "utf8" },
  );

  assert.equal(result.status, 1);
  assert.match(
    result.stderr,
    /gorin-lesson-review: SKILL\.md name must match its directory/,
  );
});

test("validate rejects a manifest domain that differs from its path", () => {
  const root = createRepositoryFixture();
  const manifestPath = join(
    root,
    "skills",
    "education",
    "gorin-lesson-review",
    "manifest.yaml",
  );
  writeFileSync(
    manifestPath,
    [
      "schema_version: 1",
      "version: 0.1.0",
      "domain: documents",
      "lifecycle: incubating",
      "ownership: first-party",
      "audience: public",
      "targets:",
      "  - agent-skills",
      "",
    ].join("\n"),
  );

  const result = spawnSync(
    process.execPath,
    [cliPath, "validate", "--root", root],
    { encoding: "utf8" },
  );

  assert.equal(result.status, 1);
  assert.match(
    result.stderr,
    /gorin-lesson-review: manifest domain must match its path \(education\)/,
  );
});

test("validate rejects lifecycle values outside the five-state model", () => {
  const root = createRepositoryFixture();
  const manifestPath = join(
    root,
    "skills",
    "education",
    "gorin-lesson-review",
    "manifest.yaml",
  );
  writeFileSync(
    manifestPath,
    [
      "schema_version: 1",
      "version: 0.1.0",
      "domain: education",
      "lifecycle: production-ready",
      "ownership: first-party",
      "audience: public",
      "targets:",
      "  - agent-skills",
      "",
    ].join("\n"),
  );

  const result = spawnSync(
    process.execPath,
    [cliPath, "validate", "--root", root],
    { encoding: "utf8" },
  );

  assert.equal(result.status, 1);
  assert.match(
    result.stderr,
    /gorin-lesson-review: unsupported lifecycle production-ready/,
  );
});

test("validate rejects capability domains outside the agreed taxonomy", () => {
  const root = createRepositoryFixture();
  const sourceDir = join(root, "skills", "education", "gorin-lesson-review");
  const skillDir = join(root, "skills", "misc", "gorin-lesson-review");
  mkdirSync(skillDir, { recursive: true });
  for (const filename of ["SKILL.md", "manifest.yaml"]) {
    const source = filename === "SKILL.md"
      ? [
          "---",
          "name: gorin-lesson-review",
          "description: Review a lesson against its approved teaching outline.",
          "---",
          "",
          "# Lesson Review",
          "",
        ].join("\n")
      : [
          "schema_version: 1",
          "version: 0.1.0",
          "domain: misc",
          "lifecycle: incubating",
          "ownership: first-party",
          "audience: public",
          "targets:",
          "  - agent-skills",
          "",
        ].join("\n");
    writeFileSync(join(skillDir, filename), source);
  }
  // Keep only the unsupported-domain skill in this fixture.
  rmSync(sourceDir, { recursive: true });

  const result = spawnSync(
    process.execPath,
    [cliPath, "validate", "--root", root],
    { encoding: "utf8" },
  );

  assert.equal(result.status, 1);
  assert.match(result.stderr, /gorin-lesson-review: unsupported domain misc/);
});

test("validate ignores the explicit legacy-v1 education directory during phased migration", () => {
  const root = createRepositoryFixture();
  const legacyDir = join(root, "skills", "edu", "legacy-lesson-review");
  mkdirSync(legacyDir, { recursive: true });
  writeFileSync(
    join(legacyDir, "SKILL.md"),
    [
      "---",
      "name: legacy-lesson-review",
      "description: A legacy skill awaiting v2 requalification.",
      "---",
      "",
      "# Legacy Lesson Review",
      "",
    ].join("\n"),
  );

  const output = execFileSync(process.execPath, [cliPath, "validate", "--root", root], {
    encoding: "utf8",
  });

  assert.equal(output, "Validated 1 skill\n");
});

test("validate requires candidate first-party skills to use the gorin namespace", () => {
  const root = mkdtempSync(join(tmpdir(), "gorin-skills-test-"));
  const skillDir = join(root, "skills", "education", "lesson-review");
  mkdirSync(skillDir, { recursive: true });
  writeFileSync(
    join(skillDir, "SKILL.md"),
    [
      "---",
      "name: lesson-review",
      "description: Review a lesson against its approved teaching outline.",
      "---",
      "",
      "# Lesson Review",
      "",
    ].join("\n"),
  );
  writeFileSync(
    join(skillDir, "manifest.yaml"),
    [
      "schema_version: 1",
      "version: 0.1.0",
      "domain: education",
      "lifecycle: candidate",
      "ownership: first-party",
      "audience: public",
      "targets:",
      "  - agent-skills",
      "",
    ].join("\n"),
  );

  const result = spawnSync(
    process.execPath,
    [cliPath, "validate", "--root", root],
    { encoding: "utf8" },
  );

  assert.equal(result.status, 1);
  assert.match(
    result.stderr,
    /lesson-review: candidate first-party skills must use the gorin- namespace/,
  );
});

test("validate rejects aliases that collide across canonical and compatibility identifiers", () => {
  const root = createRepositoryFixture();
  const secondSkill = addSkillFixture(root, {
    domain: "content",
    name: "gorin-article-outline",
    lifecycle: "incubating",
  });
  const firstManifest = join(
    root,
    "skills",
    "education",
    "gorin-lesson-review",
    "manifest.yaml",
  );
  writeFileSync(
    firstManifest,
    `${readFileSync(firstManifest, "utf8")}aliases:\n  - old-workflow\n`,
  );
  const secondManifest = join(secondSkill, "manifest.yaml");
  writeFileSync(
    secondManifest,
    `${readFileSync(secondManifest, "utf8")}aliases:\n  - old-workflow\n`,
  );

  const duplicate = spawnSync(
    process.execPath,
    [cliPath, "validate", "--root", root],
    { encoding: "utf8" },
  );
  assert.equal(duplicate.status, 1);
  assert.match(
    duplicate.stderr,
    /gorin-lesson-review: alias old-workflow is already claimed by gorin-article-outline|gorin-article-outline: alias old-workflow is already claimed by gorin-lesson-review/,
  );

  writeFileSync(
    secondManifest,
    readFileSync(secondManifest, "utf8").replace(
      "  - old-workflow",
      "  - gorin-lesson-review",
    ),
  );
  const canonicalCollision = spawnSync(
    process.execPath,
    [cliPath, "validate", "--root", root],
    { encoding: "utf8" },
  );
  assert.equal(canonicalCollision.status, 1);
  assert.match(
    canonicalCollision.stderr,
    /gorin-article-outline: alias gorin-lesson-review collides with a canonical skill identifier/,
  );
});

test("catalog writes a deterministic skill index sorted by skill identifier", () => {
  const root = createRepositoryFixture();
  const skillDir = join(root, "skills", "content", "gorin-article-outline");
  mkdirSync(skillDir, { recursive: true });
  writeFileSync(
    join(skillDir, "SKILL.md"),
    [
      "---",
      "name: gorin-article-outline",
      "description: Turn a source brief into a publication-ready article outline.",
      "---",
      "",
      "# Article Outline",
      "",
    ].join("\n"),
  );
  writeFileSync(
    join(skillDir, "manifest.yaml"),
    [
      "schema_version: 1",
      "version: 0.2.0",
      "domain: content",
      "lifecycle: incubating",
      "ownership: first-party",
      "audience: public",
      "targets:",
      "  - agent-skills",
      "  - openclaw",
      "",
    ].join("\n"),
  );
  const outputPath = join(root, "catalog", "index.json");

  for (let run = 0; run < 2; run += 1) {
    execFileSync(
      process.execPath,
      [cliPath, "catalog", "--root", root, "--output", outputPath],
      { encoding: "utf8" },
    );
  }

  assert.equal(
    readFileSync(outputPath, "utf8"),
    [
      "{",
      '  "schema_version": 1,',
      '  "skills": [',
      "    {",
      '      "id": "gorin-article-outline",',
      '      "version": "0.2.0",',
      '      "domain": "content",',
      '      "lifecycle": "incubating",',
      '      "ownership": "first-party",',
      '      "audience": "public",',
      '      "targets": [',
      '        "agent-skills",',
      '        "openclaw"',
      "      ],",
      '      "description": "Turn a source brief into a publication-ready article outline.",',
      '      "source": "skills/content/gorin-article-outline"',
      "    },",
      "    {",
      '      "id": "gorin-lesson-review",',
      '      "version": "0.1.0",',
      '      "domain": "education",',
      '      "lifecycle": "incubating",',
      '      "ownership": "first-party",',
      '      "audience": "public",',
      '      "targets": [',
      '        "agent-skills"',
      "      ],",
      '      "description": "Review a lesson against its approved teaching outline.",',
      '      "source": "skills/education/gorin-lesson-review"',
      "    }",
      "  ]",
      "}",
      "",
    ].join("\n"),
  );
});

test("build creates byte-stable packages for all four targets without executing skill code", () => {
  const root = createRepositoryFixture();
  const skillDir = join(root, "skills", "education", "gorin-lesson-review");
  writeFileSync(
    join(skillDir, "manifest.yaml"),
    [
      "schema_version: 1",
      "version: 0.1.0",
      "domain: education",
      "lifecycle: incubating",
      "ownership: first-party",
      "audience: public",
      "targets:",
      "  - agent-skills",
      "  - codex",
      "  - claude-code",
      "  - openclaw",
      "aliases:",
      "  - lesson-review",
      "adapters:",
      "  openclaw:",
      "    user_invocable: true",
      "    metadata:",
      "      requires:",
      "        bins:",
      "          - python3",
      "",
    ].join("\n"),
  );
  const scriptDir = join(skillDir, "scripts");
  const executionMarker = join(root, "skill-code-was-executed");
  mkdirSync(scriptDir);
  writeFileSync(join(scriptDir, "must-not-run.sh"), `touch ${executionMarker}\n`);
  const firstOutput = join(root, "dist-one");
  const secondOutput = join(root, "dist-two");

  const output = execFileSync(
    process.execPath,
    [cliPath, "build", "--root", root, "--skill", "gorin-lesson-review", "--output", firstOutput],
    { encoding: "utf8" },
  );
  execFileSync(
    process.execPath,
    [cliPath, "build", "--root", root, "--skill", "gorin-lesson-review", "--output", secondOutput],
    { encoding: "utf8" },
  );

  assert.equal(output, "Built gorin-lesson-review for 4 targets\n");
  for (const target of ["agent-skills", "codex", "claude-code", "openclaw"]) {
    assert.equal(
      existsSync(join(firstOutput, target, "gorin-lesson-review", "SKILL.md")),
      true,
    );
    assert.equal(
      existsSync(join(firstOutput, target, "gorin-lesson-review", "manifest.yaml")),
      false,
    );
  }
  const sourceSkill = readFileSync(join(skillDir, "SKILL.md"), "utf8");
  assert.equal(
    readFileSync(join(firstOutput, "agent-skills", "gorin-lesson-review", "SKILL.md"), "utf8"),
    sourceSkill,
  );
  assert.equal(
    readFileSync(join(firstOutput, "codex", "gorin-lesson-review", "SKILL.md"), "utf8"),
    sourceSkill,
  );
  assert.equal(
    readFileSync(join(firstOutput, "claude-code", "gorin-lesson-review", "SKILL.md"), "utf8"),
    sourceSkill,
  );
  const openclawSkill = readFileSync(
    join(firstOutput, "openclaw", "gorin-lesson-review", "SKILL.md"),
    "utf8",
  );
  assert.match(openclawSkill, /^user-invocable: true$/m);
  assert.match(
    openclawSkill,
    /^metadata: \{"openclaw":\{"requires":\{"bins":\["python3"\]\}\}\}$/m,
  );
  for (const target of ["agent-skills", "codex", "claude-code", "openclaw"]) {
    const aliasDir = join(firstOutput, target, "lesson-review");
    assert.match(
      readFileSync(join(aliasDir, "SKILL.md"), "utf8"),
      /Deprecated compatibility alias for gorin-lesson-review/,
    );
    assert.equal(existsSync(join(aliasDir, "scripts")), false);
  }
  assert.equal(existsSync(executionMarker), false);
  assert.deepEqual(snapshotTree(firstOutput), snapshotTree(secondOutput));
});

test("qualify verifies case contracts and managed installation for every declared target without mutating the repository", () => {
  const root = createRepositoryFixture();
  const qualityDir = join(
    root,
    "skills",
    "education",
    "gorin-lesson-review",
    "quality",
  );
  mkdirSync(qualityDir);
  writeFileSync(
    join(qualityDir, "cases.yaml"),
    `${JSON.stringify({
      schema_version: 1,
      positive_triggers: [
        {
          id: "review-lesson",
          prompt: "Review this lesson against its approved outline.",
          expected_route: "gorin-lesson-review",
        },
        {
          id: "find-outline-gaps",
          prompt: "Find missing outline sections in this lesson.",
          expected_route: "gorin-lesson-review",
        },
      ],
      negative_triggers: [
        {
          id: "write-lesson",
          prompt: "Write a new lesson from scratch.",
          expected_route: "not-this-skill",
        },
        {
          id: "format-markdown",
          prompt: "Fix Markdown spacing only.",
          expected_route: "not-this-skill",
        },
      ],
      golden_cases: [
        {
          id: "missing-section",
          input: "An approved outline has safety, but the lesson omits it.",
          expected_observations: ["Report the missing safety section."],
          forbidden_observations: ["Rewrite the lesson without approval."],
        },
        {
          id: "complete-lesson",
          input: "Every approved outline section is represented.",
          expected_observations: ["Report that the outline is covered."],
          forbidden_observations: ["Invent an unapproved requirement."],
        },
      ],
    }, null, 2)}\n`,
  );
  const before = snapshotTree(root);

  const report = JSON.parse(
    execFileSync(
      process.execPath,
      [
        cliPath,
        "qualify",
        "--root",
        root,
        "--skill",
        "gorin-lesson-review",
      ],
      { encoding: "utf8" },
    ),
  );

  assert.deepEqual(report, {
    schema_version: 1,
    skill: "gorin-lesson-review",
    lifecycle: "incubating",
    case_contract: {
      positive_triggers: 2,
      negative_triggers: 2,
      golden_cases: 2,
    },
    target_smoke: {
      "agent-skills": { build: "passed", install: "passed" },
    },
    runtime_output: "clean",
  });
  assert.deepEqual(snapshotTree(root), before);
});

test("install dry-run emits a stable non-mutating plan with ownership and host requirements", () => {
  const root = createRepositoryFixture();
  const skillDir = join(root, "skills", "education", "gorin-lesson-review");
  writeFileSync(
    join(skillDir, "manifest.yaml"),
    [
      "schema_version: 1",
      "version: 0.1.0",
      "domain: education",
      "lifecycle: incubating",
      "ownership: first-party",
      "audience: public",
      "targets:",
      "  - openclaw",
      "adapters:",
      "  openclaw:",
      "    user_invocable: true",
      "    metadata:",
      "      requires:",
      "        bins:",
      "          - python3",
      "        env:",
      "          - LESSON_ROOT",
      "",
    ].join("\n"),
  );
  const home = mkdtempSync(join(tmpdir(), "gorin-skills-home-"));
  const args = [
    cliPath,
    "install",
    "--dry-run",
    "--root",
    root,
    "--skill",
    "gorin-lesson-review",
    "--target",
    "openclaw",
    "--home",
    home,
  ];

  const first = execFileSync(process.execPath, args, { encoding: "utf8" });
  const second = execFileSync(process.execPath, args, { encoding: "utf8" });
  const plan = JSON.parse(first);

  assert.equal(first, second);
  assert.deepEqual(plan, {
    schema_version: 1,
    mode: "dry-run",
    skill: "gorin-lesson-review",
    version: "0.1.0",
    target: "openclaw",
    package_source: join(root, "dist", "openclaw", "gorin-lesson-review"),
    destination: join(home, ".openclaw", "skills", "gorin-lesson-review"),
    relationship: "absent",
    would_overwrite: false,
    host_requirements: {
      bins: ["python3"],
      env: ["LESSON_ROOT"],
    },
  });
  assert.equal(existsSync(join(home, ".openclaw")), false);
});

test("managed install updates transactionally and uninstall preserves unowned files", () => {
  const root = createRepositoryFixture();
  const home = mkdtempSync(join(tmpdir(), "gorin-skills-home-"));
  const skillDir = join(root, "skills", "education", "gorin-lesson-review");
  const manifestPath = join(skillDir, "manifest.yaml");
  const destination = join(home, ".codex", "skills", "gorin-lesson-review");
  const unrelated = join(home, ".codex", "skills", "unrelated", "SKILL.md");
  const receiptPath = join(
    home,
    ".local",
    "state",
    "gorin-skills",
    "receipts",
    "codex",
    "gorin-lesson-review.json",
  );
  writeFileSync(
    manifestPath,
    readFileSync(manifestPath, "utf8").replace("  - agent-skills", "  - codex"),
  );
  mkdirSync(dirname(unrelated), { recursive: true });
  writeFileSync(unrelated, "unrelated\n");

  const installArgs = [
    cliPath,
    "install",
    "--root",
    root,
    "--skill",
    "gorin-lesson-review",
    "--target",
    "codex",
    "--home",
    home,
  ];
  const firstOutput = execFileSync(process.execPath, installArgs, { encoding: "utf8" });
  assert.equal(firstOutput, "Installed gorin-lesson-review 0.1.0 for codex (managed)\n");
  assert.equal(existsSync(join(destination, "SKILL.md")), true);
  assert.equal(existsSync(join(destination, "manifest.yaml")), false);
  let receipt = JSON.parse(readFileSync(receiptPath, "utf8"));
  assert.equal(receipt.owner, "gorin-skills");
  assert.equal(receipt.mode, "managed");
  assert.equal(receipt.version, "0.1.0");
  assert.deepEqual(receipt.files.map((file) => file.path), ["SKILL.md"]);

  writeFileSync(
    manifestPath,
    readFileSync(manifestPath, "utf8").replace("version: 0.1.0", "version: 0.2.0"),
  );
  writeFileSync(
    join(skillDir, "SKILL.md"),
    readFileSync(join(skillDir, "SKILL.md"), "utf8").replace(
      "Review the supplied lesson",
      "Review version two of the supplied lesson",
    ),
  );
  const secondOutput = execFileSync(process.execPath, installArgs, { encoding: "utf8" });
  assert.equal(secondOutput, "Installed gorin-lesson-review 0.2.0 for codex (managed)\n");
  assert.match(readFileSync(join(destination, "SKILL.md"), "utf8"), /version two/);
  receipt = JSON.parse(readFileSync(receiptPath, "utf8"));
  assert.equal(receipt.version, "0.2.0");

  const receiptBeforeFailure = readFileSync(receiptPath, "utf8");
  const installedBeforeFailure = readFileSync(join(destination, "SKILL.md"), "utf8");
  writeFileSync(
    manifestPath,
    readFileSync(manifestPath, "utf8").replace("version: 0.2.0", "version: 0.3.0"),
  );
  symlinkSync(join(root, "missing-source"), join(skillDir, "broken-link"));
  const failedUpdate = spawnSync(process.execPath, installArgs, { encoding: "utf8" });
  assert.equal(failedUpdate.status, 1);
  assert.match(failedUpdate.stderr, /do not accept symbolic links/);
  assert.equal(readFileSync(receiptPath, "utf8"), receiptBeforeFailure);
  assert.equal(readFileSync(join(destination, "SKILL.md"), "utf8"), installedBeforeFailure);
  rmSync(join(skillDir, "broken-link"));

  writeFileSync(join(destination, "user-notes.txt"), "preserve me\n");
  const uninstallOutput = execFileSync(
    process.execPath,
    [
      cliPath,
      "uninstall",
      "--skill",
      "gorin-lesson-review",
      "--target",
      "codex",
      "--home",
      home,
    ],
    { encoding: "utf8" },
  );
  assert.equal(uninstallOutput, "Uninstalled gorin-lesson-review from codex; preserved 1 unowned file\n");
  assert.equal(existsSync(join(destination, "SKILL.md")), false);
  assert.equal(readFileSync(join(destination, "user-notes.txt"), "utf8"), "preserve me\n");
  assert.equal(readFileSync(unrelated, "utf8"), "unrelated\n");
  assert.equal(existsSync(receiptPath), false);
});

test("install refuses an unmanaged destination without modifying it", () => {
  const root = createRepositoryFixture();
  const home = mkdtempSync(join(tmpdir(), "gorin-skills-home-"));
  const skillDir = join(root, "skills", "education", "gorin-lesson-review");
  const manifestPath = join(skillDir, "manifest.yaml");
  writeFileSync(
    manifestPath,
    readFileSync(manifestPath, "utf8").replace("  - agent-skills", "  - codex"),
  );
  const existingSkill = join(home, ".codex", "skills", "gorin-lesson-review", "SKILL.md");
  mkdirSync(dirname(existingSkill), { recursive: true });
  writeFileSync(existingSkill, "user-owned installation\n");

  const result = spawnSync(
    process.execPath,
    [
      cliPath,
      "install",
      "--root",
      root,
      "--skill",
      "gorin-lesson-review",
      "--target",
      "codex",
      "--home",
      home,
    ],
    { encoding: "utf8" },
  );

  assert.equal(result.status, 1);
  assert.match(result.stderr, /Refusing to overwrite unmanaged destination/);
  assert.equal(readFileSync(existingSkill, "utf8"), "user-owned installation\n");
  assert.equal(
    existsSync(join(home, ".local", "state", "gorin-skills", "receipts")),
    false,
  );
});

test("link install creates and removes only its receipt-owned development link", () => {
  const root = createRepositoryFixture();
  const home = mkdtempSync(join(tmpdir(), "gorin-skills-home-"));
  const skillDir = join(root, "skills", "education", "gorin-lesson-review");
  const manifestPath = join(skillDir, "manifest.yaml");
  writeFileSync(
    manifestPath,
    readFileSync(manifestPath, "utf8").replace("  - agent-skills", "  - codex"),
  );
  const destination = join(home, ".codex", "skills", "gorin-lesson-review");
  const receiptPath = join(
    home,
    ".local",
    "state",
    "gorin-skills",
    "receipts",
    "codex",
    "gorin-lesson-review.json",
  );

  const output = execFileSync(
    process.execPath,
    [
      cliPath,
      "install",
      "--root",
      root,
      "--skill",
      "gorin-lesson-review",
      "--target",
      "codex",
      "--home",
      home,
      "--mode",
      "link",
    ],
    { encoding: "utf8" },
  );
  const receipt = JSON.parse(readFileSync(receiptPath, "utf8"));

  assert.equal(output, "Installed gorin-lesson-review 0.1.0 for codex (link)\n");
  assert.equal(lstatSync(destination).isSymbolicLink(), true);
  assert.equal(readlinkSync(destination), receipt.link_target);
  assert.equal(receipt.mode, "link");
  assert.equal(
    readFileSync(join(destination, "SKILL.md"), "utf8"),
    readFileSync(join(skillDir, "SKILL.md"), "utf8"),
  );

  execFileSync(
    process.execPath,
    [
      cliPath,
      "uninstall",
      "--skill",
      "gorin-lesson-review",
      "--target",
      "codex",
      "--home",
      home,
    ],
    { encoding: "utf8" },
  );
  assert.equal(existsSync(destination), false);
  assert.equal(existsSync(receiptPath), false);
});

test("doctor reports broken links, duplicates, legacy aliases, and the effective OpenClaw winner", () => {
  const root = createRepositoryFixture();
  const home = mkdtempSync(join(tmpdir(), "gorin-skills-home-"));
  const workspace = mkdtempSync(join(tmpdir(), "gorin-skills-workspace-"));
  const manifestPath = join(
    root,
    "skills",
    "education",
    "gorin-lesson-review",
    "manifest.yaml",
  );
  writeFileSync(
    manifestPath,
    `${readFileSync(manifestPath, "utf8")}aliases:\n  - lesson-review\n`,
  );
  const brokenLocation = join(workspace, "skills", "gorin-lesson-review");
  mkdirSync(dirname(brokenLocation), { recursive: true });
  symlinkSync(join(workspace, "missing-skill"), brokenLocation, "dir");
  const userAgentsLocation = join(home, ".agents", "skills", "gorin-lesson-review");
  const userOpenClawLocation = join(home, ".openclaw", "skills", "gorin-lesson-review");
  const legacyAliasLocation = join(home, ".openclaw", "skills", "lesson-review");
  const legacySourceLocation = join(workspace, "openclaw", "old-local-skill");
  for (const location of [userAgentsLocation, userOpenClawLocation, legacyAliasLocation]) {
    mkdirSync(location, { recursive: true });
    writeFileSync(join(location, "SKILL.md"), "---\nname: placeholder\ndescription: fixture\n---\n");
  }
  mkdirSync(legacySourceLocation, { recursive: true });
  writeFileSync(
    join(legacySourceLocation, "SKILL.md"),
    "---\nname: old-local-skill\ndescription: fixture\n---\n",
  );
  const args = [
    cliPath,
    "doctor",
    "--root",
    root,
    "--home",
    home,
    "--workspace",
    workspace,
  ];

  const first = execFileSync(process.execPath, args, { encoding: "utf8" });
  const second = execFileSync(process.execPath, args, { encoding: "utf8" });
  const report = JSON.parse(first);

  assert.equal(first, second);
  assert.deepEqual(report.broken_links, [
    {
      skill: "gorin-lesson-review",
      location: brokenLocation,
      target: join(workspace, "missing-skill"),
    },
  ]);
  assert.deepEqual(report.duplicates, [
    {
      skill: "gorin-lesson-review",
      locations: [userAgentsLocation, userOpenClawLocation],
    },
  ]);
  assert.deepEqual(report.legacy_aliases, [
    {
      alias: "lesson-review",
      canonical: "gorin-lesson-review",
      locations: [legacyAliasLocation],
    },
  ]);
  assert.deepEqual(report.legacy_source_paths, [
    {
      path: join(workspace, "openclaw"),
      skills: ["old-local-skill"],
    },
  ]);
  assert.deepEqual(report.effective.openclaw, [
    {
      skill: "gorin-lesson-review",
      winner: userAgentsLocation,
      shadowed: [userOpenClawLocation],
      ignored_broken: [brokenLocation],
    },
    {
      skill: "lesson-review",
      winner: legacyAliasLocation,
      shadowed: [],
      ignored_broken: [],
    },
  ]);
});

test("validate requires complete evidence, human approval, and documentation for promoted skills", () => {
  const root = createRepositoryFixture();
  const skillDir = join(root, "skills", "education", "gorin-lesson-review");
  const manifestPath = join(skillDir, "manifest.yaml");
  writeFileSync(
    manifestPath,
    readFileSync(manifestPath, "utf8").replace(
      "lifecycle: incubating",
      "lifecycle: promoted",
    ),
  );

  const missingEvidence = spawnSync(
    process.execPath,
    [cliPath, "validate", "--root", root],
    { encoding: "utf8" },
  );
  assert.equal(missingEvidence.status, 1);
  assert.match(missingEvidence.stderr, /promoted skill requires promotion evidence/);

  addPromotionEvidence(root, skillDir, "gorin-lesson-review");
  const output = execFileSync(
    process.execPath,
    [cliPath, "validate", "--root", root],
    { encoding: "utf8" },
  );
  assert.equal(output, "Validated 1 skill\n");
});

test("validate requires automated qualification evidence before a skill becomes candidate", () => {
  const root = createRepositoryFixture();
  const skillDir = join(root, "skills", "education", "gorin-lesson-review");
  const manifestPath = join(skillDir, "manifest.yaml");
  writeFileSync(
    manifestPath,
    readFileSync(manifestPath, "utf8").replace(
      "lifecycle: incubating",
      "lifecycle: candidate",
    ),
  );

  const missingEvidence = spawnSync(
    process.execPath,
    [cliPath, "validate", "--root", root],
    { encoding: "utf8" },
  );
  assert.equal(missingEvidence.status, 1);
  assert.match(
    missingEvidence.stderr,
    /candidate skill requires automated qualification evidence/,
  );

  const qualityDir = join(skillDir, "quality");
  mkdirSync(qualityDir);
  writeFileSync(
    join(qualityDir, "evidence.yaml"),
    [
      "schema_version: 1",
      "spec: passed",
      "schema: passed",
      "provenance_and_license: passed",
      "positive_triggers:",
      "  - review-lesson",
      "  - find-gaps",
      "negative_triggers:",
      "  - write-lesson",
      "  - format-markdown",
      "golden_cases:",
      "  - missing-section",
      "  - complete-lesson",
      "tests:",
      "  - command: node scripts/gorin-skills.mjs qualify --skill gorin-lesson-review",
      "    result: passed",
      "target_smoke:",
      "  agent-skills:",
      "    build: passed",
      "    install: passed",
      "runtime_output: clean",
      "",
    ].join("\n"),
  );
  writeFileSync(
    manifestPath,
    `${readFileSync(manifestPath, "utf8")}qualification:\n  evidence: quality/evidence.yaml\n`,
  );

  const missingCases = spawnSync(
    process.execPath,
    [cliPath, "validate", "--root", root],
    { encoding: "utf8" },
  );
  assert.equal(missingCases.status, 1);
  assert.match(missingCases.stderr, /missing quality\/cases.yaml/);

  writeFileSync(
    join(qualityDir, "cases.yaml"),
    [
      "schema_version: 1",
      "positive_triggers:",
      "  - id: review-lesson",
      "    prompt: Review a lesson against its outline.",
      "    expected_route: gorin-lesson-review",
      "  - id: find-gaps",
      "    prompt: Find missing outline sections.",
      "    expected_route: gorin-lesson-review",
      "negative_triggers:",
      "  - id: write-lesson",
      "    prompt: Write a lesson.",
      "    expected_route: not-this-skill",
      "  - id: format-markdown",
      "    prompt: Format Markdown.",
      "    expected_route: not-this-skill",
      "golden_cases:",
      "  - id: missing-section",
      "    input: A required section is absent.",
      "    expected_observations: [Report the missing section.]",
      "    forbidden_observations: [Rewrite without approval.]",
      "  - id: complete-lesson",
      "    input: Every section is present.",
      "    expected_observations: [Report complete coverage.]",
      "    forbidden_observations: [Invent requirements.]",
      "",
    ].join("\n"),
  );

  const output = execFileSync(
    process.execPath,
    [cliPath, "validate", "--root", root],
    { encoding: "utf8" },
  );
  assert.equal(output, "Validated 1 skill\n");
});

test("validate rejects non-string or blank golden observations", () => {
  const invalidCases = [
    [
      "expected_observations: [Observe the first behavior.]",
      "expected_observations: [{}]",
    ],
    [
      "forbidden_observations: [Invent another behavior.]",
      'forbidden_observations: [""]',
    ],
  ];

  for (const [validObservation, invalidObservation] of invalidCases) {
    const root = createRepositoryFixture();
    const skillDir = addSkillFixture(root, {
      domain: "content",
      name: "gorin-article-lab",
      lifecycle: "candidate",
    });
    const casesPath = join(skillDir, "quality", "cases.yaml");
    writeFileSync(
      casesPath,
      readFileSync(casesPath, "utf8").replace(
        validObservation,
        invalidObservation,
      ),
    );

    const result = spawnSync(
      process.execPath,
      [cliPath, "validate", "--root", root],
      { encoding: "utf8" },
    );

    assert.equal(result.status, 1);
    assert.match(
      result.stderr,
      /golden case observations must be non-empty strings/i,
    );
  }
});

test("validate rejects lifecycle transitions that skip required states", () => {
  const root = createRepositoryFixture();
  const manifestPath = join(
    root,
    "skills",
    "education",
    "gorin-lesson-review",
    "manifest.yaml",
  );
  writeFileSync(
    manifestPath,
    readFileSync(manifestPath, "utf8").replace(
      "lifecycle: incubating",
      "lifecycle: retired",
    ),
  );
  const baselinePath = join(root, "baseline.json");
  writeFileSync(
    baselinePath,
    `${JSON.stringify({
      schema_version: 1,
      skills: [{ id: "gorin-lesson-review", lifecycle: "promoted" }],
    }, null, 2)}\n`,
  );

  const result = spawnSync(
    process.execPath,
    [cliPath, "validate", "--root", root, "--baseline", baselinePath],
    { encoding: "utf8" },
  );

  assert.equal(result.status, 1);
  assert.match(result.stderr, /illegal lifecycle transition promoted -> retired/);
});

test("profile resolves promoted defaults and explicitly allowed non-promoted skills", () => {
  const root = createRepositoryFixture();
  const promotedDir = join(root, "skills", "education", "gorin-lesson-review");
  addPromotionEvidence(root, promotedDir, "gorin-lesson-review");
  addSkillFixture(root, {
    domain: "content",
    name: "gorin-article-lab",
    lifecycle: "candidate",
  });
  addSkillFixture(root, {
    domain: "documents",
    name: "gorin-old-export",
    lifecycle: "deprecated",
  });
  const profilesDir = join(root, "profiles");
  mkdirSync(profilesDir);
  writeFileSync(
    join(profilesDir, "default.yaml"),
    [
      "schema_version: 1",
      "name: default",
      "description: Maintained public defaults.",
      "select:",
      "  lifecycles:",
      "    - promoted",
      "",
    ].join("\n"),
  );
  writeFileSync(
    join(profilesDir, "labs.yaml"),
    [
      "schema_version: 1",
      "name: labs",
      "description: Explicit candidate selection.",
      "skills:",
      "  - gorin-article-lab",
      "allow_lifecycles:",
      "  - candidate",
      "",
    ].join("\n"),
  );

  const defaultProfile = JSON.parse(
    execFileSync(
      process.execPath,
      [cliPath, "profile", "--root", root, "--name", "default"],
      { encoding: "utf8" },
    ),
  );
  const labsProfile = JSON.parse(
    execFileSync(
      process.execPath,
      [cliPath, "profile", "--root", root, "--name", "labs"],
      { encoding: "utf8" },
    ),
  );

  assert.deepEqual(defaultProfile.skills.map((skill) => skill.id), ["gorin-lesson-review"]);
  assert.deepEqual(labsProfile.skills.map((skill) => skill.id), ["gorin-article-lab"]);
});

test("profile rejects unknown skills, duplicate selection, and inclusion cycles", () => {
  const root = createRepositoryFixture();
  const profilesDir = join(root, "profiles");
  mkdirSync(profilesDir);
  writeFileSync(
    join(profilesDir, "invalid.yaml"),
    "schema_version: 1\nname: invalid\nskills:\n  - missing-skill\n",
  );
  let result = spawnSync(
    process.execPath,
    [cliPath, "profile", "--root", root, "--name", "invalid"],
    { encoding: "utf8" },
  );
  assert.equal(result.status, 1);
  assert.match(result.stderr, /unknown skill missing-skill/);

  writeFileSync(
    join(profilesDir, "invalid.yaml"),
    [
      "schema_version: 1",
      "name: invalid",
      "skills:",
      "  - gorin-lesson-review",
      "  - gorin-lesson-review",
      "allow_lifecycles:",
      "  - incubating",
      "",
    ].join("\n"),
  );
  result = spawnSync(
    process.execPath,
    [cliPath, "profile", "--root", root, "--name", "invalid"],
    { encoding: "utf8" },
  );
  assert.equal(result.status, 1);
  assert.match(result.stderr, /duplicate selection gorin-lesson-review/);

  writeFileSync(
    join(profilesDir, "a.yaml"),
    "schema_version: 1\nname: a\nprofiles:\n  - b\n",
  );
  writeFileSync(
    join(profilesDir, "b.yaml"),
    "schema_version: 1\nname: b\nprofiles:\n  - a\n",
  );
  result = spawnSync(
    process.execPath,
    [cliPath, "profile", "--root", root, "--name", "a"],
    { encoding: "utf8" },
  );
  assert.equal(result.status, 1);
  assert.match(result.stderr, /profile inclusion cycle: a -> b -> a/);
});

test("external sources appear in the catalog but cannot be built as local skills", () => {
  const root = createRepositoryFixture();
  const registryDir = join(root, "registry", "external");
  mkdirSync(registryDir, { recursive: true });
  writeFileSync(
    join(registryDir, "matt-writing-great-skills.yaml"),
    [
      "schema_version: 1",
      "id: matt-writing-great-skills",
      "version: 1.0.0",
      "lifecycle: incubating",
      "ownership: external",
      "audience: public",
      "description: External upstream skill reference without vendored source.",
      "source:",
      "  url: https://github.com/mattpocock/skills",
      "  revision: 0123456789abcdef0123456789abcdef01234567",
      "  license: MIT",
      "",
    ].join("\n"),
  );
  const outputPath = join(root, "catalog", "index.json");

  execFileSync(
    process.execPath,
    [cliPath, "catalog", "--root", root, "--output", outputPath],
    { encoding: "utf8" },
  );
  const catalog = JSON.parse(readFileSync(outputPath, "utf8"));
  const external = catalog.skills.find((skill) => skill.id === "matt-writing-great-skills");
  assert.deepEqual(external, {
    id: "matt-writing-great-skills",
    version: "1.0.0",
    lifecycle: "incubating",
    ownership: "external",
    audience: "public",
    description: "External upstream skill reference without vendored source.",
    source_type: "external",
    source: {
      url: "https://github.com/mattpocock/skills",
      revision: "0123456789abcdef0123456789abcdef01234567",
      license: "MIT",
    },
  });
  const build = spawnSync(
    process.execPath,
    [
      cliPath,
      "build",
      "--root",
      root,
      "--skill",
      "matt-writing-great-skills",
      "--output",
      join(root, "dist"),
    ],
    { encoding: "utf8" },
  );
  assert.equal(build.status, 1);
  assert.match(build.stderr, /Unknown skill: matt-writing-great-skills/);
});

test("validate rejects an external identifier that collides with a local skill", () => {
  const root = createRepositoryFixture();
  const registryDir = join(root, "registry", "external");
  mkdirSync(registryDir, { recursive: true });
  writeFileSync(
    join(registryDir, "gorin-lesson-review.yaml"),
    [
      "schema_version: 1",
      "id: gorin-lesson-review",
      "version: 1.0.0",
      "lifecycle: incubating",
      "ownership: external",
      "audience: public",
      "description: Conflicting external registry fixture.",
      "source:",
      "  url: https://example.com/gorin-lesson-review",
      "  revision: 0123456789abcdef0123456789abcdef01234567",
      "  license: MIT",
      "",
    ].join("\n"),
  );

  const result = spawnSync(
    process.execPath,
    [cliPath, "validate", "--root", root],
    { encoding: "utf8" },
  );

  assert.equal(result.status, 1);
  assert.match(
    result.stderr,
    /duplicate skill identifier gorin-lesson-review across local and external sources/i,
  );
});

test("validate rejects an external identifier that collides with a compatibility alias", () => {
  const root = createRepositoryFixture();
  const manifestPath = join(
    root,
    "skills",
    "education",
    "gorin-lesson-review",
    "manifest.yaml",
  );
  writeFileSync(
    manifestPath,
    `${readFileSync(manifestPath, "utf8")}aliases:\n  - lesson-review\n`,
  );
  const registryDir = join(root, "registry", "external");
  mkdirSync(registryDir, { recursive: true });
  writeFileSync(
    join(registryDir, "lesson-review.yaml"),
    [
      "schema_version: 1",
      "id: lesson-review",
      "version: 1.0.0",
      "lifecycle: incubating",
      "ownership: external",
      "audience: public",
      "description: External identifier conflicting with a compatibility alias.",
      "source:",
      "  url: https://example.com/lesson-review",
      "  revision: 0123456789abcdef0123456789abcdef01234567",
      "  license: MIT",
      "",
    ].join("\n"),
  );

  const result = spawnSync(
    process.execPath,
    [cliPath, "validate", "--root", root],
    { encoding: "utf8" },
  );

  assert.equal(result.status, 1);
  assert.match(
    result.stderr,
    /duplicate skill identifier lesson-review across local and external sources/i,
  );
});

test("managed mirror validates its pinned digest and never executes upstream scripts", () => {
  const root = createRepositoryFixture();
  const mirrorDir = join(root, "skills", "engineering", "upstream-review-tool");
  mkdirSync(join(mirrorDir, "scripts"), { recursive: true });
  writeFileSync(
    join(mirrorDir, "SKILL.md"),
    "---\nname: upstream-review-tool\ndescription: Pinned upstream review instructions.\n---\n\n# Review\n",
  );
  writeFileSync(join(mirrorDir, "LICENSE"), "MIT License fixture\n");
  const executionMarker = join(root, "mirror-script-executed");
  writeFileSync(
    join(mirrorDir, "scripts", "install.sh"),
    `touch ${executionMarker}\n`,
  );
  const manifestPath = join(mirrorDir, "manifest.yaml");
  writeFileSync(
    manifestPath,
    [
      "schema_version: 1",
      "version: 1.2.3",
      "domain: engineering",
      "lifecycle: incubating",
      "ownership: managed-mirror",
      "audience: public",
      "targets:",
      "  - agent-skills",
      "provenance:",
      "  kind: mirror",
      "  upstream:",
      "    url: https://example.com/upstream/review-tool.git",
      "    revision: abcdef0123456789abcdef0123456789abcdef01",
      "  license:",
      "    spdx: MIT",
      "    file: LICENSE",
      "  content_digest: PENDING",
      "",
    ].join("\n"),
  );
  const digest = execFileSync(
    process.execPath,
    [cliPath, "digest", "--path", mirrorDir],
    { encoding: "utf8" },
  ).trim();
  writeFileSync(
    manifestPath,
    readFileSync(manifestPath, "utf8").replace("PENDING", digest),
  );

  execFileSync(
    process.execPath,
    [cliPath, "validate", "--root", root],
    { encoding: "utf8" },
  );
  execFileSync(
    process.execPath,
    [
      cliPath,
      "build",
      "--root",
      root,
      "--skill",
      "upstream-review-tool",
      "--output",
      join(root, "dist"),
    ],
    { encoding: "utf8" },
  );
  assert.equal(existsSync(executionMarker), false);

  writeFileSync(
    join(mirrorDir, "SKILL.md"),
    `${readFileSync(join(mirrorDir, "SKILL.md"), "utf8")}\nChanged without repinning.\n`,
  );
  const drifted = spawnSync(
    process.execPath,
    [cliPath, "validate", "--root", root],
    { encoding: "utf8" },
  );
  assert.equal(drifted.status, 1);
  assert.match(drifted.stderr, /managed mirror content digest mismatch/);
});

test("first-party adaptations require a gorin name and complete provenance chain", () => {
  const root = createRepositoryFixture();
  const adaptedDir = addSkillFixture(root, {
    domain: "engineering",
    name: "adapted-review",
    lifecycle: "incubating",
  });
  const manifestPath = join(adaptedDir, "manifest.yaml");
  writeFileSync(
    manifestPath,
    [
      readFileSync(manifestPath, "utf8").trimEnd(),
      "provenance:",
      "  kind: adapted",
      "  adaptation_note: Reworked prompts and tests for this repository.",
      "  sources:",
      "    - url: https://example.com/upstream/review-skill",
      "      revision: v1.0.0",
      "      license: MIT",
      "",
    ].join("\n"),
  );

  let result = spawnSync(
    process.execPath,
    [cliPath, "validate", "--root", root],
    { encoding: "utf8" },
  );
  assert.equal(result.status, 1);
  assert.match(result.stderr, /adapted first-party skills must use the gorin- namespace/);

  const renamedDir = join(root, "skills", "engineering", "gorin-adapted-review");
  mkdirSync(renamedDir, { recursive: true });
  for (const filename of ["SKILL.md", "manifest.yaml"]) {
    writeFileSync(
      join(renamedDir, filename),
      readFileSync(join(adaptedDir, filename), "utf8").replaceAll(
        "adapted-review",
        "gorin-adapted-review",
      ),
    );
  }
  rmSync(adaptedDir, { recursive: true });
  const output = execFileSync(
    process.execPath,
    [cliPath, "validate", "--root", root],
    { encoding: "utf8" },
  );
  assert.equal(output, "Validated 2 skills\n");
});

test("validate rejects dependency trees, caches, runtime outputs, and secret-shaped files", () => {
  const prohibited = [
    ["node_modules", "dependency tree"],
    [".venv", "virtual environment"],
    ["__pycache__", "cache"],
    ["out", "runtime output"],
    ["private-key.pem", "secret-shaped file"],
  ];

  for (const [name, label] of prohibited) {
    const root = createRepositoryFixture();
    const skillDir = join(root, "skills", "education", "gorin-lesson-review");
    const path = join(skillDir, name);
    if (name === "private-key.pem") {
      writeFileSync(path, "fixture-not-a-secret\n");
    } else {
      mkdirSync(path);
      writeFileSync(join(path, "fixture.txt"), "generated fixture\n");
    }
    const result = spawnSync(
      process.execPath,
      [cliPath, "validate", "--root", root],
      { encoding: "utf8" },
    );
    assert.equal(result.status, 1, label);
    assert.match(result.stderr, /prohibited repository artifact/, label);
  }
});

test("release refuses to plan without the current lifecycle baseline", () => {
  const root = createRepositoryFixture();
  const releaseDir = join(root, "release");
  const fragmentsDir = join(releaseDir, "fragments");
  const profilesDir = join(root, "profiles");
  mkdirSync(fragmentsDir, { recursive: true });
  mkdirSync(profilesDir, { recursive: true });
  writeFileSync(
    join(releaseDir, "repository.yaml"),
    "schema_version: 1\nversion: 2.0.0\n",
  );
  writeFileSync(
    join(fragmentsDir, "lesson-review.yaml"),
    "schema_version: 1\nsummary: Improve lesson review.\nrepository: patch\nskills:\n  gorin-lesson-review: patch\n",
  );
  writeFileSync(
    join(profilesDir, "default.yaml"),
    "schema_version: 1\nname: default\nselect:\n  lifecycles:\n    - promoted\n",
  );

  const result = spawnSync(
    process.execPath,
    [cliPath, "release", "--dry-run", "--root", root],
    { encoding: "utf8" },
  );

  assert.equal(result.status, 1);
  assert.match(
    result.stderr,
    /missing lifecycle baseline .*release\/baselines\/catalog-2\.0\.0\.json/i,
  );
  assert.equal(existsSync(join(root, "catalog", "index.json")), false);
});

test("release dry-run and apply derive every artifact from one multi-skill version plan", () => {
  const root = createRepositoryFixture();
  addSkillFixture(root, {
    domain: "content",
    name: "gorin-article-lab",
    lifecycle: "candidate",
    version: "1.4.2",
  });
  const releaseDir = join(root, "release");
  const fragmentsDir = join(releaseDir, "fragments");
  const profilesDir = join(root, "profiles");
  mkdirSync(fragmentsDir, { recursive: true });
  mkdirSync(profilesDir, { recursive: true });
  writeFileSync(
    join(releaseDir, "repository.yaml"),
    "schema_version: 1\nversion: 2.0.0\n",
  );
  const baselinesDir = join(releaseDir, "baselines");
  mkdirSync(baselinesDir);
  writeFileSync(
    join(baselinesDir, "catalog-2.0.0.json"),
    `${JSON.stringify({
      schema_version: 1,
      catalog_version: "2.0.0",
      skills: [
        { id: "gorin-article-lab", lifecycle: "candidate" },
        { id: "gorin-lesson-review", lifecycle: "incubating" },
      ],
    }, null, 2)}\n`,
  );
  writeFileSync(
    join(profilesDir, "default.yaml"),
    "schema_version: 1\nname: default\nselect:\n  lifecycles:\n    - promoted\n",
  );
  const fragmentPath = join(fragmentsDir, "education-improvements.yaml");
  writeFileSync(
    fragmentPath,
    [
      "schema_version: 1",
      "summary: Improve lesson review and article lab behavior.",
      "repository: minor",
      "skills:",
      "  gorin-lesson-review: minor",
      "  gorin-article-lab: patch",
      "",
    ].join("\n"),
  );
  const lessonManifest = join(
    root,
    "skills",
    "education",
    "gorin-lesson-review",
    "manifest.yaml",
  );
  const lessonBefore = readFileSync(lessonManifest, "utf8");

  const dryRun = JSON.parse(
    execFileSync(
      process.execPath,
      [cliPath, "release", "--dry-run", "--root", root],
      { encoding: "utf8" },
    ),
  );
  assert.deepEqual(dryRun.repository, { from: "2.0.0", to: "2.1.0", bump: "minor" });
  assert.deepEqual(dryRun.skills, [
    { id: "gorin-article-lab", from: "1.4.2", to: "1.4.3", bump: "patch" },
    { id: "gorin-lesson-review", from: "0.1.0", to: "0.2.0", bump: "minor" },
  ]);
  assert.deepEqual(dryRun.fragments, ["education-improvements.yaml"]);
  assert.equal(readFileSync(lessonManifest, "utf8"), lessonBefore);
  assert.equal(existsSync(join(root, "catalog", "index.json")), false);

  const output = execFileSync(
    process.execPath,
    [cliPath, "release", "--root", root],
    { encoding: "utf8" },
  );
  assert.equal(output, "Released repository 2.1.0 with 2 skill updates\n");
  assert.match(readFileSync(lessonManifest, "utf8"), /version: 0\.2\.0/);
  assert.match(
    readFileSync(
      join(root, "skills", "content", "gorin-article-lab", "manifest.yaml"),
      "utf8",
    ),
    /version: 1\.4\.3/,
  );
  assert.match(readFileSync(join(releaseDir, "repository.yaml"), "utf8"), /version: 2\.1\.0/);
  const catalog = JSON.parse(readFileSync(join(root, "catalog", "index.json"), "utf8"));
  assert.equal(catalog.catalog_version, "2.1.0");
  assert.equal(
    catalog.skills.find((skill) => skill.id === "gorin-lesson-review").version,
    "0.2.0",
  );
  const defaultLock = JSON.parse(
    readFileSync(join(releaseDir, "profiles", "default.lock.json"), "utf8"),
  );
  assert.equal(defaultLock.repository_version, "2.1.0");
  assert.equal(
    existsSync(
      join(
        releaseDir,
        "packages",
        "agent-skills",
        "gorin-lesson-review",
        "SKILL.md",
      ),
    ),
    true,
  );
  assert.equal(
    readFileSync(join(releaseDir, "baselines", "catalog-2.1.0.json"), "utf8"),
    readFileSync(join(root, "catalog", "index.json"), "utf8"),
  );
  assert.match(readFileSync(join(root, "CHANGELOG.md"), "utf8"), /## 2\.1\.0/);
  assert.equal(existsSync(fragmentPath), false);
  assert.equal(
    existsSync(
      join(releaseDir, "consumed", "2.1.0", "education-improvements.yaml"),
    ),
    true,
  );

  const noFragments = spawnSync(
    process.execPath,
    [cliPath, "release", "--dry-run", "--root", root],
    { encoding: "utf8" },
  );
  assert.equal(noFragments.status, 1);
  assert.match(noFragments.stderr, /No release fragments/);
});

test("release rejects malformed fragments before changing any version", () => {
  const root = createRepositoryFixture();
  const releaseDir = join(root, "release");
  const fragmentsDir = join(releaseDir, "fragments");
  mkdirSync(fragmentsDir, { recursive: true });
  writeFileSync(
    join(releaseDir, "repository.yaml"),
    "schema_version: 1\nversion: 2.0.0\n",
  );
  const baselinesDir = join(releaseDir, "baselines");
  mkdirSync(baselinesDir);
  writeFileSync(
    join(baselinesDir, "catalog-2.0.0.json"),
    `${JSON.stringify({
      schema_version: 1,
      catalog_version: "2.0.0",
      skills: [
        { id: "gorin-lesson-review", lifecycle: "incubating" },
      ],
    }, null, 2)}\n`,
  );
  const fragmentPath = join(fragmentsDir, "invalid.yaml");
  const repositoryBefore = readFileSync(join(releaseDir, "repository.yaml"), "utf8");

  for (const [source, errorPattern] of [
    [
      "schema_version: 1\nrepository: patch\nskills:\n  gorin-lesson-review: patch\n",
      /release fragment summary must be non-empty/,
    ],
    [
      "schema_version: 1\nsummary: Unknown skill.\nrepository: patch\nskills:\n  missing-skill: patch\n",
      /unknown skill missing-skill/,
    ],
    [
      "schema_version: 1\nsummary: Bad bump.\nrepository: tiny\nskills:\n  gorin-lesson-review: patch\n",
      /unsupported semantic increment tiny/,
    ],
  ]) {
    writeFileSync(fragmentPath, source);
    const result = spawnSync(
      process.execPath,
      [cliPath, "release", "--dry-run", "--root", root],
      { encoding: "utf8" },
    );
    assert.equal(result.status, 1);
    assert.match(result.stderr, errorPattern);
    assert.equal(readFileSync(join(releaseDir, "repository.yaml"), "utf8"), repositoryBefore);
  }
});

test("release generation failure leaves manifests, repository version, and fragments untouched", () => {
  const root = createRepositoryFixture();
  const releaseDir = join(root, "release");
  const fragmentsDir = join(releaseDir, "fragments");
  mkdirSync(fragmentsDir, { recursive: true });
  writeFileSync(
    join(releaseDir, "repository.yaml"),
    "schema_version: 1\nversion: 2.0.0\n",
  );
  const fragmentPath = join(fragmentsDir, "valid.yaml");
  writeFileSync(
    fragmentPath,
    "schema_version: 1\nsummary: Valid change.\nrepository: patch\nskills:\n  gorin-lesson-review: patch\n",
  );
  const manifestPath = join(
    root,
    "skills",
    "education",
    "gorin-lesson-review",
    "manifest.yaml",
  );
  const manifestBefore = readFileSync(manifestPath, "utf8");
  const repositoryBefore = readFileSync(join(releaseDir, "repository.yaml"), "utf8");
  symlinkSync(join(root, "missing"), join(dirname(manifestPath), "broken-input"));

  const result = spawnSync(
    process.execPath,
    [cliPath, "release", "--root", root],
    { encoding: "utf8" },
  );

  assert.equal(result.status, 1);
  assert.match(result.stderr, /do not accept symbolic links/);
  assert.equal(readFileSync(manifestPath, "utf8"), manifestBefore);
  assert.equal(readFileSync(join(releaseDir, "repository.yaml"), "utf8"), repositoryBefore);
  assert.equal(existsSync(fragmentPath), true);
  assert.equal(existsSync(join(root, "catalog", "index.json")), false);
});

test("inventory accounts for every local skill once and generates a legally filtered legacy profile", () => {
  const root = createRepositoryFixture();
  writeFileSync(join(root, "LICENSE"), "MIT License fixture\n");
  const marker = join(root, "legacy-script-executed");
  const legacySkills = [
    {
      path: ["openclaw", "custom-workflow"],
      body: `Use /Users/alice/private/project and install under ~/.openclaw/skills.\n`,
      meta: '{"origin":"self","author":"fixture"}\n',
    },
    {
      path: ["openclaw", "baoyu-demo"],
      body: "Third-party mirror without local license evidence.\n",
    },
    {
      path: ["openclaw", "docx"],
      body: "Restricted office skill.\n",
      license: "Distribution prohibited by fixture license.\n",
    },
    {
      path: ["openclaw", "md2pdf"],
      body: "Adapted from an MIT upstream without bundled attribution.\n",
      meta: '{"origin":"adapted from upstream (MIT License)"}\n',
    },
    {
      path: ["skills", "edu", "gorin-edu-old"],
      body: "Legacy first-party education instructions.\n",
    },
  ];
  for (const legacy of legacySkills) {
    const name = legacy.path.at(-1);
    const directory = join(root, ...legacy.path);
    mkdirSync(join(directory, "scripts"), { recursive: true });
    writeFileSync(
      join(directory, "SKILL.md"),
      `---\nname: ${name}\ndescription: Fixture ${name}.\n---\n\n${legacy.body}`,
    );
    writeFileSync(join(directory, "scripts", "install.sh"), `touch ${marker}\n`);
    if (legacy.meta) writeFileSync(join(directory, ".skill-meta.json"), legacy.meta);
    if (legacy.license) writeFileSync(join(directory, "LICENSE.txt"), legacy.license);
  }
  const runtimeOutput = join(root, "openclaw", "custom-workflow", "out", "result.md");
  mkdirSync(dirname(runtimeOutput), { recursive: true });
  writeFileSync(runtimeOutput, "generated output\n");
  execFileSync("git", ["init", "-q"], { cwd: root });
  execFileSync("git", ["add", "."], { cwd: root });
  const outputPath = join(root, "inventory", "skills.json");
  const profilePath = join(root, "profiles", "legacy-v1.yaml");

  const output = execFileSync(
    process.execPath,
    [
      cliPath,
      "inventory",
      "--root",
      root,
      "--output",
      outputPath,
      "--legacy-profile",
      profilePath,
    ],
    { encoding: "utf8" },
  );
  const inventory = JSON.parse(readFileSync(outputPath, "utf8"));

  assert.equal(output, "Inventoried 6 local skills (5 legacy-v1, 1 v2)\n");
  assert.equal(inventory.skills.length, 6);
  assert.equal(new Set(inventory.skills.map((skill) => skill.path)).size, 6);
  assert.equal(inventory.summary.legacy_v1, 5);
  assert.equal(inventory.summary.v2, 1);
  assert.equal(
    inventory.skills.find((skill) => skill.id === "baoyu-demo").source_type,
    "managed-mirror",
  );
  assert.equal(
    inventory.skills.find((skill) => skill.id === "md2pdf").source_type,
    "adapted-first-party",
  );
  assert.equal(
    inventory.skills.find((skill) => skill.id === "docx").license.status,
    "restricted",
  );
  const custom = inventory.skills.find((skill) => skill.id === "custom-workflow");
  assert.deepEqual(custom.findings.personal_absolute_paths, ["SKILL.md"]);
  assert.deepEqual(custom.findings.hard_coded_install_roots, [
    { root: "~/.openclaw/skills", files: ["SKILL.md"] },
  ]);
  assert.deepEqual(custom.findings.tracked_runtime_artifacts, ["out/result.md"]);
  assert.equal(existsSync(marker), false);

  const legacyProfile = JSON.parse(
    execFileSync(
      process.execPath,
      [cliPath, "profile", "--root", root, "--name", "legacy-v1"],
      { encoding: "utf8" },
    ),
  );
  assert.deepEqual(legacyProfile.skills.map((skill) => skill.id), [
    "custom-workflow",
    "gorin-edu-old",
  ]);
  assert.equal(legacyProfile.end_of_support, "before-repository-major-3");
});

test("migrate consumes inventory to move a legacy source without executing its scripts", () => {
  const root = createRepositoryFixture();
  writeFileSync(join(root, "LICENSE"), "MIT License fixture\n");
  const legacyDir = join(root, "skills", "edu", "gorin-edu-old");
  const marker = join(root, "migration-script-executed");
  mkdirSync(join(legacyDir, "scripts"), { recursive: true });
  writeFileSync(
    join(legacyDir, "SKILL.md"),
    [
      "---",
      "name: gorin-edu-old",
      "description: Legacy education workflow.",
      "homepage: https://example.com/gorin-edu-old",
      "user-invocable: true",
      "---",
      "",
      "# Legacy Education Workflow",
      "",
    ].join("\n"),
  );
  writeFileSync(
    join(legacyDir, ".skill-meta.json"),
    '{"version":"0.3.0","origin":"self"}\n',
  );
  writeFileSync(join(legacyDir, "scripts", "install.sh"), `touch ${marker}\n`);
  execFileSync("git", ["init", "-q"], { cwd: root });
  execFileSync("git", ["add", "."], { cwd: root });
  execFileSync(
    process.execPath,
    [cliPath, "inventory", "--root", root],
    { encoding: "utf8" },
  );

  const output = execFileSync(
    process.execPath,
    [cliPath, "migrate", "--root", root, "--domain", "education"],
    { encoding: "utf8" },
  );
  const migratedDir = join(root, "skills", "education", "gorin-edu-old");

  assert.equal(output, "Migrated 1 legacy skill into education\n");
  assert.equal(existsSync(legacyDir), false);
  assert.equal(existsSync(migratedDir), true);
  assert.equal(existsSync(join(migratedDir, ".skill-meta.json")), false);
  assert.match(readFileSync(join(migratedDir, "manifest.yaml"), "utf8"), /version: 0\.3\.0/);
  assert.match(
    readFileSync(join(migratedDir, "manifest.yaml"), "utf8"),
    /homepage: https:\/\/example\.com\/gorin-edu-old/,
  );
  assert.doesNotMatch(
    readFileSync(join(migratedDir, "SKILL.md"), "utf8"),
    /user-invocable|homepage/,
  );
  assert.equal(existsSync(marker), false);
  assert.equal(
    execFileSync(
      process.execPath,
      [cliPath, "validate", "--root", root],
      { encoding: "utf8" },
    ),
    "Validated 2 skills\n",
  );
});
