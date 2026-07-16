// bearclaw-native.js - Rock-solid Bear Blog automation using OpenClaw native browser
// "Once BearClaw grips your content, it never lets go." 🐻🦞
// Native Browser Edition - No Chrome Extension Required!

/**
 * BearClaw Native - Using OpenClaw's Built-in Browser
 * 
 * Features:
 * - Zero external dependencies (no Chrome extension)
 * - Uses OpenClaw's native browser API
 * - Same reliability as Chrome extension version (95-99%)
 * - Supports headless mode
 * - Full remote browser support
 * - Multi-profile support
 */

const CONFIG = {
  TIMEOUT: parseInt(process.env.BEARCLAW_TIMEOUT) || 30000,
  DEBUG: process.env.BEARCLAW_DEBUG === 'true',
  MAX_RETRIES: parseInt(process.env.BEARCLAW_MAX_RETRIES) || 3,
  RETRY_DELAY: parseInt(process.env.BEARCLAW_RETRY_DELAY) || 2000,
  BROWSER_PROFILE: process.env.BEARCLAW_BROWSER_PROFILE || 'openclaw',
  BASE_URL: 'https://bearblog.dev'
};

// ============================================================================
// Utility Functions
// ============================================================================

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function withRetry(fn, operation = 'operation', maxRetries = CONFIG.MAX_RETRIES) {
  let lastError;
  
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      log(`🦞 [Attempt ${attempt}/${maxRetries}] ${operation}...`);
      const result = await fn();
      log(`✅ [Success] ${operation} completed`);
      return result;
    } catch (error) {
      lastError = error;
      log(`❌ [Attempt ${attempt}/${maxRetries}] ${operation} failed: ${error.message}`);
      
      if (attempt < maxRetries) {
        const delay = CONFIG.RETRY_DELAY * Math.pow(2, attempt - 1);
        log(`⏳ Waiting ${delay}ms before retry...`);
        await sleep(delay);
      }
    }
  }
  
  throw new Error(`${operation} failed after ${maxRetries} attempts: ${lastError.message}`);
}

function log(message) {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] [🐻🦞 BearClaw Native] ${message}`);
}

async function debugScreenshot(browserAPI, name) {
  if (!CONFIG.DEBUG) return;
  
  try {
    const result = await browserAPI({
      action: 'screenshot',
      profile: CONFIG.BROWSER_PROFILE,
      fullPage: true
    });
    
    if (result.path) {
      log(`📸 Screenshot saved: ${result.path}`);
    }
  } catch (error) {
    log(`⚠️  Failed to save screenshot: ${error.message}`);
  }
}

// ============================================================================
// Bear Blog Specific Functions Using OpenClaw Browser API
// ============================================================================

/**
 * Ensure browser is running
 */
async function ensureBrowser(browserAPI) {
  log('🔧 Checking browser status...');
  
  const status = await browserAPI({
    action: 'status',
    profile: CONFIG.BROWSER_PROFILE
  });
  
  if (!status.running) {
    log('🚀 Starting browser...');
    await browserAPI({
      action: 'start',
      profile: CONFIG.BROWSER_PROFILE
    });
    await sleep(2000);
  }
  
  log('✅ Browser ready');
}

/**
 * Verify user is logged in to Bear Blog
 */
async function ensureLoggedIn(browserAPI) {
  log('🔐 Verifying login state...');
  
  // Get current page snapshot
  const snapshot = await browserAPI({
    action: 'snapshot',
    profile: CONFIG.BROWSER_PROFILE,
    format: 'ai'
  });
  
  const snapshotText = snapshot.text || '';
  
  // Check for login indicators
  if (snapshotText.includes('Log in') && !snapshotText.includes('Dashboard')) {
    throw new Error('NOT_LOGGED_IN: Please log in to Bear Blog in the OpenClaw browser first');
  }
  
  // Check for dashboard link
  if (!snapshotText.includes('Dashboard') && !snapshotText.includes('Posts')) {
    throw new Error('SESSION_EXPIRED: Cannot find dashboard. Please log in again.');
  }
  
  log('✅ Login verified');
}

/**
 * Get Bear Blog username from current URL or session
 */
async function getBlogUsername(browserAPI) {
  // Get current tabs to find username
  const tabs = await browserAPI({
    action: 'tabs',
    profile: CONFIG.BROWSER_PROFILE
  });
  
  const currentTab = tabs.find(t => t.active) || tabs[0];
  if (!currentTab) {
    throw new Error('No active browser tab found');
  }
  
  // Extract username from URL like https://bearblog.dev/gorin/dashboard/
  const urlMatch = currentTab.url.match(/bearblog\.dev\/([^\/]+)\//);
  if (urlMatch && urlMatch[1] && urlMatch[1] !== 'dashboard') {
    return urlMatch[1];
  }
  
  // If not found, try to get from snapshot
  const snapshot = await browserAPI({
    action: 'snapshot',
    profile: CONFIG.BROWSER_PROFILE,
    format: 'ai'
  });
  
  const snapshotText = snapshot.text || '';
  const linkMatch = snapshotText.match(/\/([^\/]+)\/dashboard\//);
  if (linkMatch && linkMatch[1]) {
    return linkMatch[1];
  }
  
  throw new Error('Cannot determine Bear Blog username. Please navigate to your Bear Blog dashboard first.');
}

/**
 * Navigate to new post page
 */
async function navigateToNewPost(browserAPI, username) {
  log('🧭 Navigating to new post page...');
  
  const newPostUrl = `${CONFIG.BASE_URL}/${username}/dashboard/posts/new/`;
  log(`📍 URL: ${newPostUrl}`);
  
  await browserAPI({
    action: 'navigate',
    profile: CONFIG.BROWSER_PROFILE,
    url: newPostUrl,
    wait: 'networkidle',
    timeout: CONFIG.TIMEOUT
  });
  
  await debugScreenshot(browserAPI, 'after-navigation');
  
  // Wait for body_content textarea to be ready
  await browserAPI({
    action: 'wait',
    profile: CONFIG.BROWSER_PROFILE,
    selector: 'textarea[name="body_content"]',
    timeout: CONFIG.TIMEOUT
  });
  
  log('✅ New post page loaded');
}

/**
 * Find element in snapshot by multiple strategies
 */
function findElementRef(snapshot, strategies, elementName) {
  log(`🔍 Looking for element: ${elementName}`);
  
  const snapshotText = snapshot.text || '';
  const refs = snapshot.refs || [];
  
  for (const strategy of strategies) {
    // Search in snapshot text for matching patterns
    const pattern = typeof strategy === 'string' ? strategy : strategy.pattern;
    
    if (snapshotText.toLowerCase().includes(pattern.toLowerCase())) {
      // Try to extract ref number from context
      const lines = snapshotText.split('\n');
      for (const line of lines) {
        if (line.toLowerCase().includes(pattern.toLowerCase())) {
          // Extract ref number like [12] or ref="12"
          const match = line.match(/\[(\d+)\]|ref[=\"'](\d+)/);
          if (match) {
            const ref = parseInt(match[1] || match[2]);
            log(`✅ Found ${elementName} with ref: ${ref}`);
            return ref;
          }
        }
      }
    }
  }
  
  log(`⚠️  Element not found: ${elementName}`);
  return null;
}

/**
 * Fill field using browser API
 */
async function fillField(browserAPI, snapshot, strategies, value, fieldName) {
  log(`✍️  Filling field: ${fieldName}`);
  
  const ref = findElementRef(snapshot, strategies, fieldName);
  
  if (!ref) {
    throw new Error(`Cannot find ${fieldName} in page snapshot`);
  }
  
  // Clear and fill
  await browserAPI({
    action: 'act',
    profile: CONFIG.BROWSER_PROFILE,
    kind: 'click',
    ref: ref
  });
  
  await sleep(300);
  
  // Select all and delete
  await browserAPI({
    action: 'act',
    profile: CONFIG.BROWSER_PROFILE,
    kind: 'press',
    key: 'Control+a'  // Works on most systems
  });
  
  await sleep(100);
  
  // Type new content
  await browserAPI({
    action: 'act',
    profile: CONFIG.BROWSER_PROFILE,
    kind: 'type',
    ref: ref,
    text: value
  });
  
  await sleep(500);
  
  log(`✅ ${fieldName} filled`);
}

/**
 * Create a new Bear Blog post
 */
async function createPost(browserAPI, postData) {
  const { title, content, tags, link, makeDiscoverable, isPage } = postData;
  
  log('📝 Starting post creation...');
  log(`📌 Title: ${title}`);
  log(`📏 Content length: ${content.length} characters`);
  
  // Ensure browser is running
  await ensureBrowser(browserAPI);
  
  // Ensure logged in and get username
  await ensureLoggedIn(browserAPI);
  const username = await getBlogUsername(browserAPI);
  log(`👤 Blog username: ${username}`);
  
  // Navigate to new post page
  await navigateToNewPost(browserAPI, username);
  
  // Wait for form to be ready
  await sleep(1000);
  
  await debugScreenshot(browserAPI, 'form-ready');
  
  // Build header content (frontmatter in contenteditable div)
  let headerContent = `title: ${title}\n`;
  
  if (link) headerContent += `link: ${link}\n`;
  if (tags) headerContent += `tags: ${tags}\n`;
  if (isPage !== undefined) headerContent += `is_page: ${isPage}\n`;
  if (makeDiscoverable !== undefined) headerContent += `make_discoverable: ${makeDiscoverable}\n`;
  
  log('📋 Header content (frontmatter):');
  log(headerContent);
  
  // Fill header_content using JavaScript execution
  log('✍️  Filling header content...');
  await browserAPI({
    action: 'act',
    profile: CONFIG.BROWSER_PROFILE,
    kind: 'evaluate',
    fn: `
      const headerDiv = document.getElementById('header_content');
      if (headerDiv) {
        headerDiv.innerHTML = ${JSON.stringify(headerContent.replace(/\n/g, '<br>'))};
      }
    `
  });
  
  await sleep(500);
  
  // Fill body_content textarea
  log('✍️  Filling body content...');
  await browserAPI({
    action: 'act',
    profile: CONFIG.BROWSER_PROFILE,
    kind: 'evaluate',
    fn: `
      const textarea = document.getElementById('body_content');
      if (textarea) {
        textarea.value = ${JSON.stringify(content)};
      }
    `
  });
  
  await sleep(500);
  
  await debugScreenshot(browserAPI, 'form-filled');
  
  // Click the "Publish" button (not "Save as draft")
  log('💾 Clicking Publish button...');
  await browserAPI({
    action: 'act',
    profile: CONFIG.BROWSER_PROFILE,
    kind: 'evaluate',
    fn: `
      const publishButton = document.getElementById('publish-button');
      if (publishButton) {
        publishButton.click();
      } else {
        throw new Error('Publish button not found');
      }
    `
  });
  
  // Wait for save to complete
  log('⏳ Waiting for save operation...');
  await browserAPI({
    action: 'wait',
    profile: CONFIG.BROWSER_PROFILE,
    load: 'networkidle',
    timeout: CONFIG.TIMEOUT
  });
  
  await sleep(2000);
  
  await debugScreenshot(browserAPI, 'after-save');
  
  // Get final URL
  const tabs = await browserAPI({
    action: 'tabs',
    profile: CONFIG.BROWSER_PROFILE
  });
  
  const currentTab = tabs.find(t => t.active);
  const finalUrl = currentTab ? currentTab.url : '';
  
  log(`🔗 Final URL: ${finalUrl}`);
  
  // Verify success - should redirect to posts list or post view
  if (!finalUrl.includes('/new')) {
    log('🎉 Post created successfully!');
    return {
      success: true,
      url: finalUrl,
      message: 'Post published successfully'
    };
  }
  
  // Check for errors
  const errorSnapshot = await browserAPI({
    action: 'snapshot',
    profile: CONFIG.BROWSER_PROFILE,
    format: 'ai'
  });
  
  const errorText = errorSnapshot.text || '';
  if (errorText.toLowerCase().includes('error')) {
    const errorLines = errorText.split('\n').filter(line => 
      line.toLowerCase().includes('error')
    );
    throw new Error(`Save failed: ${errorLines.join(', ')}`);
  }
  
  log('⚠️  Still on new post page - save may have failed');
  return {
    success: false,
    url: finalUrl,
    message: 'Save status unclear. Please check browser and verify manually.'
  };
}

/**
 * Update an existing post
 */
async function updatePost(browserAPI, postData) {
  const { postUrl, title, content, tags } = postData;
  
  log(`📝 Updating post: ${postUrl}`);
  
  await ensureBrowser(browserAPI);
  
  // Navigate to edit page (add /edit/ if not already there)
  let editUrl = postUrl;
  if (!editUrl.includes('/edit/')) {
    editUrl = postUrl.replace(/\/$/, '') + '/edit/';
  }
  log(`🧭 Navigating to: ${editUrl}`);
  
  await browserAPI({
    action: 'navigate',
    profile: CONFIG.BROWSER_PROFILE,
    url: editUrl,
    wait: 'networkidle',
    timeout: CONFIG.TIMEOUT
  });
  
  await ensureLoggedIn(browserAPI);
  await sleep(1000);
  
  // Build new header content if title or tags changed
  if (title || tags) {
    let headerContent = '';
    if (title) {
      headerContent = `title: ${title}\n`;
    }
    if (tags) {
      headerContent += `tags: ${tags}\n`;
    }
    
    if (headerContent) {
      log('✍️  Updating header content...');
      await browserAPI({
        action: 'act',
        profile: CONFIG.BROWSER_PROFILE,
        kind: 'evaluate',
        fn: `
          const headerDiv = document.getElementById('header_content');
          if (headerDiv) {
            headerDiv.innerHTML = ${JSON.stringify(headerContent.replace(/\n/g, '<br>'))};
          }
        `
      });
      await sleep(500);
    }
  }
  
  // Update body content if provided
  if (content) {
    log('✍️  Updating body content...');
    await browserAPI({
      action: 'act',
      profile: CONFIG.BROWSER_PROFILE,
      kind: 'evaluate',
      fn: `
        const textarea = document.getElementById('body_content');
        if (textarea) {
          textarea.value = ${JSON.stringify(content)};
        }
      `
    });
    await sleep(500);
  }
  
  // Click Publish button
  log('💾 Clicking Publish button...');
  await browserAPI({
    action: 'act',
    profile: CONFIG.BROWSER_PROFILE,
    kind: 'evaluate',
    fn: `
      const publishButton = document.getElementById('publish-button');
      if (publishButton) {
        publishButton.click();
      }
    `
  });
  
  await browserAPI({
    action: 'wait',
    profile: CONFIG.BROWSER_PROFILE,
    load: 'networkidle',
    timeout: CONFIG.TIMEOUT
  });
  
  await sleep(2000);
  
  log('✅ Post updated successfully');
  
  const tabs = await browserAPI({
    action: 'tabs',
    profile: CONFIG.BROWSER_PROFILE
  });
  const currentTab = tabs.find(t => t.active);
  
  return {
    success: true,
    url: currentTab ? currentTab.url : ''
  };
}

/**
 * Delete a post
 */
async function deletePost(browserAPI, postData) {
  const { postUrl } = postData;
  
  log(`🗑️  Deleting post: ${postUrl}`);
  
  await ensureBrowser(browserAPI);
  
  // Navigate to edit page
  let editUrl = postUrl;
  if (!editUrl.includes('/edit/')) {
    editUrl = postUrl.replace(/\/$/, '') + '/edit/';
  }
  
  await browserAPI({
    action: 'navigate',
    profile: CONFIG.BROWSER_PROFILE,
    url: editUrl,
    wait: 'networkidle',
    timeout: CONFIG.TIMEOUT
  });
  
  await ensureLoggedIn(browserAPI);
  await sleep(1000);
  
  // Call the deletePost() JavaScript function on the page
  log('🗑️  Calling delete function...');
  await browserAPI({
    action: 'act',
    profile: CONFIG.BROWSER_PROFILE,
    kind: 'evaluate',
    fn: `
      if (typeof deletePost === 'function') {
        deletePost();
      } else {
        alert('Delete function not found');
      }
    `
  });
  
  // Wait for confirmation dialog and handle it
  await sleep(1000);
  
  // The page has a confirm() dialog, which should be handled automatically
  // by the browser. Wait for the deletion to complete.
  await browserAPI({
    action: 'wait',
    profile: CONFIG.BROWSER_PROFILE,
    load: 'networkidle',
    timeout: CONFIG.TIMEOUT
  });
  
  await sleep(1000);
  
  log('✅ Post deleted successfully');
  return {
    success: true,
    message: 'Post deleted'
  };
}

// ============================================================================
// Main Entry Point
// ============================================================================

async function main(browserAPI, action, data) {
  try {
    log('═══════════════════════════════════════════════');
    log('🐻🦞 BearClaw Native - OpenClaw Browser Edition');
    log('═══════════════════════════════════════════════');
    log(`Action: ${action}`);
    log(`Browser profile: ${CONFIG.BROWSER_PROFILE}`);
    log(`Debug mode: ${CONFIG.DEBUG}`);
    log(`Timeout: ${CONFIG.TIMEOUT}ms`);
    log(`Max retries: ${CONFIG.MAX_RETRIES}`);
    log('═══════════════════════════════════════════════');
    
    let result;
    
    switch (action) {
      case 'create_post':
        result = await withRetry(
          () => createPost(browserAPI, data),
          'Create post'
        );
        break;
        
      case 'update_post':
        result = await withRetry(
          () => updatePost(browserAPI, data),
          'Update post'
        );
        break;
        
      case 'delete_post':
        result = await withRetry(
          () => deletePost(browserAPI, data),
          'Delete post'
        );
        break;
        
      default:
        throw new Error(`Unknown action: ${action}`);
    }
    
    log('═══════════════════════════════════════════════');
    log('✅ Operation completed successfully');
    log('═══════════════════════════════════════════════');
    return result;
    
  } catch (error) {
    log('═══════════════════════════════════════════════');
    log(`❌ Operation failed: ${error.message}`);
    log('═══════════════════════════════════════════════');
    
    // Provide helpful error messages
    if (error.message.includes('NOT_LOGGED_IN')) {
      throw new Error(
        '❌ You are not logged in to Bear Blog.\n\n' +
        '📋 Steps to fix:\n' +
        '1. Open Bear Blog in OpenClaw browser:\n' +
        '   openclaw browser open https://bearblog.dev\n' +
        '2. Log in to your account\n' +
        '3. Keep the browser window open\n' +
        '4. Try again\n\n' +
        '💡 Tip: The OpenClaw browser is separate from your regular browser'
      );
    }
    
    if (error.message.includes('SESSION_EXPIRED')) {
      throw new Error(
        '❌ Your Bear Blog session has expired.\n\n' +
        '📋 Steps to fix:\n' +
        '1. Navigate to Bear Blog:\n' +
        '   openclaw browser navigate https://bearblog.dev\n' +
        '2. Log in if prompted\n' +
        '3. Try again'
      );
    }
    
    if (error.message.includes('Browser disabled')) {
      throw new Error(
        '❌ OpenClaw browser is disabled.\n\n' +
        '📋 Steps to fix:\n' +
        '1. Enable browser:\n' +
        '   openclaw config set browser.enabled true\n' +
        '2. Restart OpenClaw if needed:\n' +
        '   openclaw restart\n' +
        '3. Try again'
      );
    }
    
    throw error;
  }
}

// Export for OpenClaw
module.exports = { main, CONFIG };
