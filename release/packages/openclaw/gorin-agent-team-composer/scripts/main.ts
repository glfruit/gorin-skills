import { mkdirSync, readFileSync, writeFileSync } from "fs";
import { dirname, join, resolve } from "path";

type ChannelPlatform = "telegram" | "discord" | "wechat";
type WorkflowMode = "serial" | "parallel" | "hybrid";

interface AgentSpec {
  name: string;
  slug: string;
  responsibility: string;
  role: string;
  domain: string;
  expertise: string;
  model: string;
  maxRetries: number;
}

interface TeamSpec {
  teamName: string;
  teamSlug: string;
  objective: string;
  workflowMode: WorkflowMode;
  platforms: ChannelPlatform[];
  alertChannel: string;
  reportChannel: string;
  defaultChannel: string;
  maxConcurrent: number;
  timeoutPerAgent: number;
  timeoutTotal: number;
  agents: AgentSpec[];
}

interface TemplateData {
  team_name: string;
  team_slug: string;
  team_role: string;
  objective: string;
  workflow_mode_label: string;
  workflow_mode_desc: string;
  platforms: string;
  alert_channel: string;
  report_channel: string;
  default_channel: string;
  max_concurrent: string;
  timeout_per_agent: string;
  timeout_total: string;
  responsibilities_md: string;
  agent_table_md: string;
  contacts_table_md: string;
  platforms_yaml: string;
  agents_yaml: string;
  coordination_principles_md: string;
}

const DEFAULT_MODEL = process.env.ATC_DEFAULT_MODEL || "zai/glm-5-turbo";
const OPENCLAW_CONFIG_PATH =
  process.env.OPENCLAW_CONFIG || resolve(process.env.HOME || "/root", ".openclaw/openclaw.json");
const TEMPLATE_DIR = resolve(dirname(process.argv[1] || __dirname), "team");

// --- Model scanning ---

type ModelTier = "quality-first" | "balanced" | "throughput-first";

interface ModelInfo {
  id: string;           // e.g. "glm-5-turbo"
  provider: string;     // e.g. "zai"
  qualified: string;    // e.g. "zai/glm-5-turbo"
  contextWindow: number;
  maxTokens: number;
}

interface ModelPool {
  all: ModelInfo[];
  byTier: Record<ModelTier, ModelInfo[]>;
}

// Tier preferences: ordered from best to worst for each tier
const TIER_ORDER: Record<ModelTier, string[]> = {
  "quality-first": [
    // Prefer reasoning models from premium providers
    "openai-codex/gpt-5.4",
    "openai-codex/gpt-5.3-codex",
    "zai/glm-5",
    "zai/glm-5-turbo",
    "minimax/MiniMax-M2.5",
  ],
  "balanced": [
    "zai/glm-5-turbo",
    "openai-codex/gpt-5.3-codex-spark",
    "zai/glm-5",
    "minimax/MiniMax-M2.5",
    "zai/glm-4.7",
  ],
  "throughput-first": [
    "zai/glm-4.7-flashx",
    "zai/glm-4.7-flash",
    "zai/glm-4.7",
    "kimi-coding/k2p5",
    "zai/glm-5-turbo",
  ],
};

function scanModels(configPath: string): ModelPool {
  const pool: ModelPool = { all: [], byTier: { "quality-first": [], balanced: [], "throughput-first": [] } };

  try {
    const raw = JSON.parse(readFileSync(configPath, "utf8"));
    const providers = raw?.models?.providers;
    if (!providers) return pool;

    // Collect all available models
    for (const [provider, cfg] of Object.entries(providers) as [string, { models?: Array<{ id: string; contextWindow?: number; maxTokens?: number; compat?: { supportsTools?: boolean } }> }][]) {
      for (const m of cfg.models || []) {
        // Skip models that can't use tools
        if (m.compat?.supportsTools === false) continue;
        pool.all.push({
          id: m.id,
          provider,
          qualified: `${provider}/${m.id}`,
          contextWindow: m.contextWindow || 0,
          maxTokens: m.maxTokens || 0,
        });
      }
    }

    // Sort each tier: prefer models in TIER_ORDER order, then by context window desc
    for (const tier of ["quality-first", "balanced", "throughput-first"] as ModelTier[]) {
      const preference = TIER_ORDER[tier];
      const available = new Set(pool.all.map((m) => m.qualified));
      const tierModels: ModelInfo[] = [];

      // First add models in preference order
      for (const qualified of preference) {
        const m = pool.all.find((x) => x.qualified === qualified);
        if (m) tierModels.push(m);
      }

      // Then add remaining models not in preference list
      for (const m of pool.all) {
        if (!tierModels.includes(m)) tierModels.push(m);
      }

      pool.byTier[tier] = tierModels;
    }
  } catch {
    // Silently fall back to DEFAULT_MODEL if config can't be read
  }

  return pool;
}

function pickModel(tier: ModelTier, pool: ModelPool): string {
  const models = pool.byTier[tier];
  return models.length > 0 ? models[0].qualified : DEFAULT_MODEL;
}

function pickFallbacks(tier: ModelTier, pool: ModelPool, primary: string): string[] {
  const models = pool.byTier[tier];
  return models
    .filter((m) => m.qualified !== primary)
    .slice(0, 3)
    .map((m) => m.qualified);
}

function classifyAgentTier(name: string, responsibility: string): ModelTier {
  const text = `${name} ${responsibility}`;
  // Quality-first: decision makers, reviewers, risk managers
  if (/(主管|协调|经理|leader|lead|pm|风控|审核|review|risk|guard|tl$)/i.test(text)) {
    return "quality-first";
  }
  // Throughput-first: scanners, monitors, collectors
  if (/(雷达|搜集|扫描|监控|scout|monitor|watcher|collector|采集)/i.test(text)) {
    return "throughput-first";
  }
  // Default: balanced
  return "balanced";
}

function usage(): void {
  console.error(
    'Usage: npx ts-node scripts/main.ts "<团队描述>" [--output-dir <dir>]',
  );
  process.exit(1);
}

function slugify(input: string): string {
  const ascii = input
    .trim()
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, "-")
    .replace(/^-+|-+$/g, "");
  return ascii || "team";
}

function classifyAgent(name: string, responsibility: string): Pick<AgentSpec, "role" | "domain" | "expertise"> {
  const text = `${name} ${responsibility}`;
  if (/(主管|协调|经理|leader|lead|pm)/i.test(text)) {
    return { role: "Team Lead", domain: "coordination", expertise: "planning, routing, closure" };
  }
  if (/(雷达|搜集|研究|scout|research)/i.test(text)) {
    return { role: "Research Scout", domain: "research", expertise: "search, filtering, evidence capture" };
  }
  if (/(撰写|写作|writer|copy)/i.test(text)) {
    return { role: "Writer", domain: "writing", expertise: "drafting, structure, narrative delivery" };
  }
  if (/(审核|review|critic|校对)/i.test(text)) {
    return { role: "Reviewer", domain: "review", expertise: "critique, verification, quality gates" };
  }
  if (/(设计|visual|design)/i.test(text)) {
    return { role: "Designer", domain: "design", expertise: "visual communication, layout, assets" };
  }
  return { role: "Specialist", domain: slugify(name), expertise: responsibility };
}

function parseWorkflowMode(input: string): WorkflowMode {
  if (/(串行|顺序|serial)/i.test(input)) return "serial";
  if (/(并行|parallel)/i.test(input)) return "parallel";
  return "hybrid";
}

function parsePlatforms(input: string): ChannelPlatform[] {
  const out: ChannelPlatform[] = [];
  if (/(telegram)/i.test(input)) out.push("telegram");
  if (/(discord)/i.test(input)) out.push("discord");
  if (/(微信|wechat)/i.test(input)) out.push("wechat");
  return out.length ? out : ["telegram"];
}

function parseAgents(input: string, modelPool: ModelPool): AgentSpec[] {
  const specs: AgentSpec[] = [];
  const regex = /(?:^|\n)\s*-\s*([^:：\n]+?)\s*[：:]\s*(?:负责|responsible\s+for)\s*([^\n]+)/gi;
  for (const match of input.matchAll(regex)) {
    const name = match[1].trim();
    const responsibility = match[2].trim().replace(/[。；;]+$/u, "");
    const info = classifyAgent(name, responsibility);
    const tier = classifyAgentTier(name, responsibility);
    const primary = pickModel(tier, modelPool);
    const fallbacks = pickFallbacks(tier, modelPool, primary);
    specs.push({
      name,
      slug: slugify(name),
      responsibility,
      role: info.role,
      domain: info.domain,
      expertise: info.expertise,
      model: primary,
      maxRetries: 3,
      _tier: tier,
      _fallbacks: fallbacks,
    } as AgentSpec & { _tier: ModelTier; _fallbacks: string[] });
  }
  if (specs.length) {
    return specs;
  }

  const inlineBlock =
    input.match(/团队包括[：:]\s*([^\n]+)/u)?.[1] ||
    input.match(/包括\s*([^。！!\n]+)/u)?.[1] ||
    "";
  if (!inlineBlock) {
    return specs;
  }

  const names = inlineBlock
    .split(/[、，,]/u)
    .map((item) => item.trim())
    .filter(Boolean);

  for (const name of names) {
    const info = classifyAgent(name, name);
    const tier = classifyAgentTier(name, name);
    const primary = pickModel(tier, modelPool);
    const fallbacks = pickFallbacks(tier, modelPool, primary);
    specs.push({
      name,
      slug: slugify(name),
      responsibility: `${name}相关工作`,
      role: info.role,
      domain: info.domain,
      expertise: info.expertise,
      model: primary,
      maxRetries: 3,
      _tier: tier,
      _fallbacks: fallbacks,
    } as AgentSpec & { _tier: ModelTier; _fallbacks: string[] });
  }
  return specs;
}

function parseTeamName(input: string): string {
  const m =
    input.match(/(?:组建|创建|设计|搭建|帮我组建一个?)\s*([^，。,\n]+?团队)/u) ||
    input.match(/你是一个\s*([^，。,\n]+?团队)/u);
  return m?.[1]?.trim() || "新团队";
}

function parseObjective(input: string): string {
  const m =
    input.match(/致力于\s*([^。！!\n]+)/u) ||
    input.match(/目标[：:]\s*([^\n]+)/u);
  return m?.[1]?.trim() || "高效完成多智能体协作任务";
}

function parseChannelValue(input: string, key: "告警通道" | "日报输出"): string {
  const re = new RegExp(`${key}\\s*[：:]\\s*([^\\n]+)`, "u");
  return input.match(re)?.[1]?.trim() || "";
}

/** Normalize input: split single-line "- item - item - item" into separate lines. */
function buildTeamSpec(input: string, modelPool: ModelPool): TeamSpec {
  // Normalize: split single-line "- A：负责xxx - B：负责yyy - C：负责zzz" into separate lines
  // Strategy: find lines with multiple inline agents, split on " - " before "Name：" patterns
  const normalizedInput = input
    .split("\n")
    .map((line) => {
      if (!/^\s*-\s*[^\n]*[：:]/.test(line)) return line;
      // Count inline agents: "- Name：xxx" where Name has no colon
      const agentParts = line.split(/\s+-\s+(?=[^\n]*[：:])/);
      if (agentParts.length <= 1) return line;
      return agentParts.map((p, i) => {
        const trimmed = p.trim();
        if (i === 0) return trimmed; // first part already has "- "
        // Subsequent parts: the " - " was consumed by split, add it back
        return "- " + trimmed;
      }).join("\n");
    })
    .join("\n");

  const teamName = parseTeamName(normalizedInput);
  const workflowMode = parseWorkflowMode(normalizedInput);
  const agents = parseAgents(normalizedInput, modelPool);
  if (!agents.length) {
    throw new Error("未能从输入中识别团队成员。请使用 `- 成员名：负责职责` 的格式。");
  }
  const alertChannel = parseChannelValue(normalizedInput, "告警通道") || "pending-alert-channel";
  const reportChannel = parseChannelValue(normalizedInput, "日报输出") || "pending-report-channel";
  const maxConcurrent = workflowMode === "serial" ? 1 : Math.min(Math.max(agents.length, 2), 6);
  const timeoutPerAgent = 300;
  const timeoutTotal =
    workflowMode === "serial"
      ? timeoutPerAgent * agents.length
      : workflowMode === "parallel"
        ? timeoutPerAgent * 2
        : Math.max(timeoutPerAgent * 2, timeoutPerAgent + 120 * agents.length);

  return {
    teamName,
    teamSlug: slugify(teamName),
    objective: parseObjective(normalizedInput),
    workflowMode,
    platforms: parsePlatforms(normalizedInput),
    alertChannel,
    reportChannel,
    defaultChannel: reportChannel,
    maxConcurrent,
    timeoutPerAgent,
    timeoutTotal,
    agents,
  };
}

function workflowModeLabel(mode: WorkflowMode): string {
  if (mode === "serial") return "串行";
  if (mode === "parallel") return "并行";
  return "混合";
}

function workflowModeDescription(mode: WorkflowMode): string {
  if (mode === "serial") return "串行协作：上一位成员的输出是下一位成员的输入，适合审核链和依赖明确的流程。";
  if (mode === "parallel") return "并行协作：多个成员同时处理不同子任务，再由 TL 汇总，适合采集、分析和生产并发任务。";
  return "混合协作：并行采集与串行审核结合，适合真实团队的多阶段任务。";
}

function toTemplateData(spec: TeamSpec): TemplateData {
  return {
    team_name: spec.teamName,
    team_slug: spec.teamSlug,
    team_role: `${spec.teamName}协调团队`,
    objective: spec.objective,
    workflow_mode_label: workflowModeLabel(spec.workflowMode),
    workflow_mode_desc: workflowModeDescription(spec.workflowMode),
    platforms: spec.platforms.join(", "),
    platforms_yaml: spec.platforms.map((p) => `  - "${p}"`).join("\n"),
    alert_channel: spec.alertChannel,
    report_channel: spec.reportChannel,
    default_channel: spec.defaultChannel,
    max_concurrent: String(spec.maxConcurrent),
    timeout_per_agent: String(spec.timeoutPerAgent),
    timeout_total: String(spec.timeoutTotal),
    responsibilities_md: spec.agents.map((a) => `- ${a.name}：负责 ${a.responsibility}`).join("\n"),
    agent_table_md: spec.agents
      .map((a) => `| ${a.name} | ${a.role} | ${a.domain} | ${a.responsibility} |`)
      .join("\n"),
    contacts_table_md: spec.agents
      .map((a) => `| ${a.name} | @${a.slug} | ${a.expertise} | ${a.responsibility} |`)
      .join("\n"),
    agents_yaml: spec.agents
      .map((a) => {
        const extra = a as AgentSpec & { _tier?: string; _fallbacks?: string[] };
        const fallbacks = extra._fallbacks?.length
          ? `\n    fallbacks:\n${extra._fallbacks.map((f) => `      - "${f}"`).join("\n")}`
          : "";
        const tierComment = extra._tier ? `  # tier: ${extra._tier}` : "";
        return `  - name: "${a.name}"
    slug: "${a.slug}"
    role: "${a.role}"
    domain: "${a.domain}"
    responsibility: "${a.responsibility}"
    config:
      model: "${a.model}"${tierComment}${fallbacks}
      max_retries: ${a.maxRetries}`;
      })
      .join("\n"),
    coordination_principles_md: [
      "- 接到任务先分解，再分配，不重复劳动。",
      "- 关键节点必须回传状态，不允许静默失败。",
      "- 输出统一进入 TL 汇总，再对外反馈。",
    ].join("\n"),
  };
}

function render(template: string, data: TemplateData): string {
  let output = template;
  for (const [key, value] of Object.entries(data)) {
    output = output.replace(new RegExp(`{{${key}}}`, "g"), value);
  }
  return output;
}

function template(name: string): string {
  return readFileSync(join(TEMPLATE_DIR, name), "utf8");
}

function generate(spec: TeamSpec, outputRoot: string): string {
  const outDir = resolve(outputRoot, spec.teamSlug);
  mkdirSync(outDir, { recursive: true });
  const data = toTemplateData(spec);
  const files: Record<string, string> = {
    "SOUL.md": render(template("soul-template.md"), data),
    "AGENTS.md": render(template("agents-template.md"), data),
    "CollaborationRules.md": render(template("collaboration-rules-template.md"), data),
    "Contacts.md": render(template("team-contacts.md"), data),
    "agent-config.yaml": render(template("agent-config.yaml"), data),
  };
  for (const [name, content] of Object.entries(files)) {
    writeFileSync(join(outDir, name), content);
  }
  return outDir;
}

function parseArgs(argv: string[]): { prompt: string; outputDir: string } {
  const args = [...argv];
  let outputDir = process.cwd();
  const outputIdx = args.indexOf("--output-dir");
  if (outputIdx >= 0) {
    const value = args[outputIdx + 1];
    if (!value) usage();
    outputDir = resolve(value);
    args.splice(outputIdx, 2);
  }
  const prompt = args.join(" ").trim();
  if (!prompt) usage();
  return { prompt, outputDir };
}

function main(): void {
  const { prompt, outputDir } = parseArgs(process.argv.slice(2));
  const modelPool = scanModels(OPENCLAW_CONFIG_PATH);
  const spec = buildTeamSpec(prompt, modelPool);
  const outDir = generate(spec, outputDir);
  console.log(`generated: ${outDir}`);
  console.log(`team: ${spec.teamName}`);
  console.log(`agents: ${spec.agents.length}`);
  console.log(`workflow: ${workflowModeLabel(spec.workflowMode)}`);
  console.log(`platforms: ${spec.platforms.join(", ")}`);
  console.log(`models scanned: ${modelPool.all.length}`);
  // Print model assignment summary
  console.log("\nModel assignments:");
  for (const a of spec.agents) {
    const extra = a as AgentSpec & { _tier?: string; _fallbacks?: string[] };
    console.log(`  ${a.name}: ${a.model} (${extra._tier || "default"})${extra._fallbacks?.length ? ` → ${extra._fallbacks.join(", ")}` : ""}`);
  }
}

if (require.main === module) {
  main();
}
