// 使用方式：node teaching-slides.js --course "课程名" --task "任务名" --theme engineering --output output.pptx
// 或者 require('./teaching-slides') 然后调用 API

const pptxgen = require("pptxgenjs");
const path = require("path");
const fs = require("fs");

// 主题配置
const THEMES = {
  engineering: {
    primary: "2C5F2D", secondary: "97BC62", accent: "F5F5F5", dark: "1A3C2A",
    titleFont: "Georgia", bodyFont: "Calibri", codeFont: "Consolas"
  },
  computing: {
    primary: "065A82", secondary: "1C7293", accent: "E0F7FA", dark: "21295C",
    titleFont: "Calibri", bodyFont: "Calibri", codeFont: "Consolas"
  },
  humanities: {
    primary: "B85042", secondary: "E7E8D1", accent: "A7BEAE", dark: "4A3728",
    titleFont: "Palatino", bodyFont: "Garamond", codeFont: "Consolas"
  },
  general: {
    primary: "36454F", secondary: "708090", accent: "028090", dark: "212121",
    titleFont: "Calibri", bodyFont: "Calibri", codeFont: "Consolas"
  },
  safety: {
    primary: "1A2332", secondary: "2D8B8B", accent: "F1FAEE", dark: "212121",
    titleFont: "Calibri", bodyFont: "Calibri", codeFont: "Consolas",
    danger: "E63946"
  }
};

// 解析命令行参数
function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i].startsWith("--")) {
      opts[args[i].slice(2)] = args[i + 1] || "";
      i++;
    }
  }
  return opts;
}

// 构建演示文稿
function buildPresentation({ courseName, taskName, themeName, outputPath, slides }) {
  const theme = THEMES[themeName] || THEMES.general;
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.author = "Edu Squad";
  pres.title = `${courseName} - ${taskName}`;

  // 为每张幻灯片提供便捷方法
  function addSlide(content) {
    const slide = pres.addSlide();
    if (content.background) slide.background = { color: content.background };
    if (content.elements) content.elements.forEach(el => {
      switch (el.type) {
        case "text":
          slide.addText(el.text, {
            x: el.x, y: el.y, w: el.w || 9, h: el.h || 1,
            fontSize: el.fontSize || 16, fontFace: el.fontFace || theme.bodyFont,
            color: el.color || theme.dark, bold: el.bold || false,
            align: el.align || "left", valign: el.valign || "top",
            margin: el.margin !== undefined ? el.margin : 0
          });
          break;
        case "shape":
          slide.addShape(pres.shapes.RECTANGLE, {
            x: el.x, y: el.y, w: el.w || 1, h: el.h || 1,
            fill: { color: el.fill || theme.accent }
          });
          break;
        case "table":
          slide.addTable(el.data, {
            x: el.x, y: el.y, w: el.w || 9,
            border: { pt: 1, color: "CCCCCC" },
            fontSize: el.fontSize || 13,
            fontFace: theme.bodyFont,
            color: theme.dark,
            autoPage: false
          });
          break;
        case "code":
          // 代码块：深色背景 + 等宽字体
          slide.addShape(pres.shapes.RECTANGLE, {
            x: el.x || 0.5, y: el.y || 0.5, w: el.w || 9, h: el.h || 4,
            fill: { color: "36454F" }, rectRadius: 0.05
          });
          slide.addText(el.code, {
            x: (el.x || 0.5) + 0.2, y: (el.y || 0.5) + 0.15,
            w: (el.w || 9) - 0.4, h: (el.h || 4) - 0.3,
            fontSize: el.fontSize || 12, fontFace: theme.codeFont,
            color: "E0E0E0", valign: "top", margin: 0
          });
          break;
      }
    });
    return slide;
  }

  // 标准封面页
  function addTitleSlide() {
    return addSlide({
      background: theme.dark,
      elements: [
        { type: "text", text: courseName, x: 0.5, y: 1.0, w: 9, h: 1, fontSize: 28, fontFace: theme.titleFont, color: theme.secondary, align: "center", bold: true },
        { type: "text", text: taskName, x: 0.5, y: 2.0, w: 9, h: 1.5, fontSize: 44, fontFace: theme.titleFont, color: "FFFFFF", align: "center", bold: true }
      ]
    });
  }

  // 标准内容页
  function addContentSlide(title, bullets) {
    return addSlide({
      background: theme.accent,
      elements: [
        // 左侧色带
        { type: "shape", x: 0, y: 0, w: 0.08, h: 5.625, fill: theme.primary },
        // 标题
        { type: "text", text: title, x: 0.5, y: 0.3, w: 9, h: 0.8, fontSize: 28, fontFace: theme.titleFont, color: theme.dark, bold: true },
        // 内容
        { type: "text", text: bullets.map(b => ({ text: b, options: { bullet: true, breakLine: true } })), x: 0.5, y: 1.3, w: 9, h: 3.8, fontSize: 16, fontFace: theme.bodyFont, color: theme.dark }
      ]
    });
  }

  // 标准表格页
  function addTableSlide(title, headers, rows) {
    return addSlide({
      background: theme.accent,
      elements: [
        { type: "shape", x: 0, y: 0, w: 0.08, h: 5.625, fill: theme.primary },
        { type: "text", text: title, x: 0.5, y: 0.3, w: 9, h: 0.8, fontSize: 28, fontFace: theme.titleFont, color: theme.dark, bold: true },
        { type: "table", x: 0.5, y: 1.3, w: 9, data: [headers.map(h => ({ text: h, options: { fill: { color: theme.primary }, color: "FFFFFF", bold: true } })), ...rows.map(row => row.map(cell => ({ text: cell })))] }
      ]
    });
  }

  // 标准结束页
  function addEndSlide() {
    return addSlide({
      background: theme.dark,
      elements: [
        { type: "text", text: "谢谢！", x: 0.5, y: 1.5, w: 9, h: 1.5, fontSize: 44, fontFace: theme.titleFont, color: "FFFFFF", align: "center", bold: true }
      ]
    });
  }

  return { pres, addSlide, addTitleSlide, addContentSlide, addTableSlide, addEndSlide, theme, THEMES };
}

// CLI 模式
if (require.main === module) {
  const args = parseArgs();
  const { pres, addTitleSlide, addContentSlide, addTableSlide, addEndSlide } = buildPresentation({
    courseName: args.course || "课程名",
    taskName: args.task || "任务名",
    themeName: args.theme || "general",
    outputPath: args.output || "output.pptx"
  });

  // 生成示例页面
  addTitleSlide();
  addContentSlide("知识目标", ["目标一", "目标二", "目标三"]);
  addContentSlide("技能目标", ["技能一", "技能二"]);
  addTableSlide("常用代码", ["代码", "名称", "功能"], [["G00", "快速定位", "说明"], ["G01", "直线插补", "说明"]]);
  addEndSlide();

  pres.writeFile({ fileName: args.output || "output.pptx" }).then(() => {
    console.log("✅ Generated:", args.output || "output.pptx");
  });
}

module.exports = { buildPresentation, THEMES };
