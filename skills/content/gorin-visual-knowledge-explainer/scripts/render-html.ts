// render-html.ts - Generate HTML from content and template

/**
 * Render HTML page from template and content
 * Returns complete HTML string
 */

import { readFileSync } from 'fs';

/**
 * Load template from file
 */
export function loadTemplate(templatePath: string): string {
  try {
    return readFileSync(templatePath, 'utf-8');
  } catch (error) {
    throw new Error(`Failed to load template: ${templatePath}`);
  }
}

/**
 * Render HTML with placeholders replaced
 */
export function renderHtml(template: string, params: Record<string, string>): string {
  let result = template;
  
  // Replace placeholders
  for (const [key, value] of Object.entries(params)) {
    const regex = new RegExp(`\\{${key}\\}`, 'g');
    result = result.replace(regex, value);
  }
  
  return result;
}

/**
 * Generate metadata HTML
 */
export function generateMetadataHtml(metadata: Record<string, string>): string {
  const entries = Object.entries(metadata);
  if (entries.length === 0) return '';
  
  const html = entries.map(([key, value]) => `<span>${key}: ${value}</span>`).join(' ');
  return `<div class="metadata">${html}</div>`;
}

/**
 * Generate learning objectives HTML
 */
export function generateLearningObjectivesHtml(objectives: string[]): string {
  if (objectives.length === 0) return '';
  
  const listItems = objectives.map(obj => `<li>${obj}</li>`).join('');
  return `
    <section class="learning-objectives">
      <h2>Learning Objectives</h2>
      <ul>${listItems}</ul>
    </section>
  `;
}

/**
 * Generate summary HTML
 */
export function generateSummaryHtml(summary: string): string {
  if (!summary) return '';
  
  return `
    <section class="summary">
      <h2>小结</h2>
      <p>${summary}</p>
    </section>
  `;
}

/**
 * Generate reference section HTML
 */
export function generateReferenceHtml(items: string[]): string {
  if (items.length === 0) return '';
  
  const listItems = items.map(item => `<li>${item}</li>`).join('');
  return `
    <section class="reference">
      <h2>参考</h2>
      <ul>${listItems}</ul>
    </section>
  `;
}

/**
 * Generate module HTML
 */
export function generateModuleHtml(title: string, content: string, options: {
  example?: string;
  mistakes?: string[];
  practice?: string;
} = {}): string {
  const { example, mistakes = [], practice } = options;
  
  let html = `
    <article class="module">
      <h3>${title}</h3>
      ${content}
  `;
  
  if (example) {
    html += `
      <div class="example">
        <h4>示例</h4>
        <pre><code>${example}</code></pre>
      </div>
    `;
  }
  
  if (mistakes.length > 0) {
    const listItems = mistakes.map(m => `<li>${m}</li>`).join('');
    html += `
      <div class="common-mistakes">
        <h4>常见错误</h4>
        <ul>${listItems}</ul>
      </div>
    `;
  }
  
  if (practice) {
    html += `
      <div class="practice">
        <h4>练习</h4>
        <p>${practice}</p>
      </div>
    `;
  }
  
  html += '</article>';
  return html;
}

/**
 * Generate workflow steps HTML
 */
export function generateWorkflowStepsHtml(steps: { title: string; content: string; code?: string }[]): string {
  const stepHtml = steps.map(step => {
    let html = `
      <div class="step">
        <h3>${step.title}</h3>
        ${step.content}
    `;
    
    if (step.code) {
      html += `<pre><code>${step.code}</code></pre>`;
    }
    
    html += '</div>';
    return html;
  }).join('\n');
  
  return `<section class="workflow-steps">${stepHtml}</section>`;
}

/**
 * Generate comparison table HTML
 */
export function generateComparisonTableHtml(headers: string[], rows: string[][]): string {
  const headersHtml = `<tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr>`;
  const rowsHtml = rows.map(row => `<tr>${row.map(cell => `<td>${cell}</td>`).join('')}</tr>`).join('');
  
  return `
    <table>
      <thead>${headersHtml}</thead>
      <tbody>${rowsHtml}</tbody>
    </table>
  `;
}

/**
 * Generate slide HTML (for slide-deck template)
 */
export function generateSlideHtml(title: string, content: string, isTitle = false): string {
  const className = isTitle ? 'slide title-slide' : 'slide content-slide';
  
  return `
    <section class="${className}">
      <h1>${title}</h1>
      <p>${content}</p>
    </section>
  `;
}
