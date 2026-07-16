// select-template.ts - Select appropriate HTML template based on content type

// Template mapping: content type -> template filename
export const templateMap: Record<string, string> = {
  教材: 'chapter-explainer.html',
  培训: 'training-page.html',
  知识讲解: 'explainer-page.html',
  流程: 'workflow-page.html',
  对比: 'comparison-table.html',
  技术: 'explainer-page.html',  // fallback to generic explainer
  默认: 'explainer-page.html',
};

// Theme mapping: content type -> theme name
export const themeMap: Record<string, string> = {
  教材: 'grace',
  培训: 'simple',
  知识讲解: 'grace',
  流程: 'simple',
  对比: 'default',
  技术: 'modern',
  默认: 'default',
};

/**
 * Select template based on content type
 */
export function selectTemplate(contentType: string): string {
  const template = templateMap[contentType] || templateMap['默认'];
  return template;
}

/**
 * Select theme based on content type
 */
export function selectTheme(contentType: string): string {
  const theme = themeMap[contentType] || themeMap['默认'];
  return theme;
}

/**
 * Get recommended template and theme
 */
export function recommendRenderStrategy(contentType: string): { template: string; theme: string } {
  return {
    template: selectTemplate(contentType),
    theme: selectTheme(contentType),
  };
}
