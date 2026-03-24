// detect-content-type.ts - Automatically detect content type
// Uses simple keyword matching to classify content

/**
 * Detect content type from markdown/text content
 * Returns: '教材' | '培训' | '知识讲解' | '流程' | '对比' | '技术' | '未知'
 */

export function detectContentType(content: string): string {
  const lowerContent = content.toLowerCase();
  
  // 教材 signals
  if (hasKeyword(lowerContent, ['教程', '教学', '课堂', '课程', '教材', '讲义', '学习目标'])) {
    return '教材';
  }
  
  // 培训 signals
  if (hasKeyword(lowerContent, ['SOP', '培训', '操作手册', '工作流程', '步骤说明', 'FAQ'])) {
    return '培训';
  }
  
  // 流程 signals
  if (hasKeyword(lowerContent, ['流程', 'workflow', 'step', '步骤'])) {
    return '流程';
  }
  
  // 对比 signals
  if (hasKeyword(lowerContent, ['对比', 'vs', ' versus ', '比较', '差异', '区别'])) {
    return '对比';
  }
  
  // 知识讲解 signals (读书笔记/知识卡)
  if (hasKeyword(lowerContent, ['笔记', '读书', '概念', '知识点', '含义', '解释'])) {
    return '知识讲解';
  }
  
  // 技术说明 signals
  if (hasKeyword(lowerContent, ['架构', '模块', '系统', '技术', 'API', '数据库', '服务器'])) {
    return '技术';
  }
  
  return '未知';
}

function hasKeyword(text: string, keywords: string[]): boolean {
  return keywords.some(keyword => text.includes(keyword));
}
