"""
InfiniteWeb Official Prompts Library
=====================================
Organized by functional category following the paper's workflow.

Categories:
1. Task Generation - Generate user tasks from website seed
2. Interface Design - Design APIs for tasks and pages
3. Architecture Design - Design page structure and navigation
4. Page Design - Design page functionality and layout
5. Page Generation - Generate HTML/CSS code
6. Data Generation - Generate realistic website data
7. Backend Generation - Generate business logic and tests
8. Evaluator Generation - Generate task completion evaluators
9. Instrumentation - Add tracking for task completion
"""

# =============================================================================
# 1. TASK GENERATION
# =============================================================================

PROMPT_TASK_GENERATION = """
You are a UX researcher. Generate {task_count_range} realistic user tasks for a {website_type}.
IMPORTANT REQUIREMENTS:
1. This is a mock website, so tasks should NOT depend on any external services like email authentication.
2. Each task MUST contain between {min_steps}-{max_steps} detailed steps for proper complexity.
3. Tasks should be suitable for RL model training, requiring multiple decisions and interactions.
Each task should:
• Represent a SPECIFIC user goal with MEASURABLE success criteria
• Contain {min_steps}-{max_steps} DETAILED action steps
• Include CLEAR decision criteria (e.g., "select the cheapest option", "choose items with 4+ stars")
• Specify EXACT targets (e.g., "add 3 items under $50", "find products with free shipping")
• Use CONCRETE values and thresholds (prices, quantities, ratings, dates)
• Cover different aspects of the website functionality
Task specificity requirements:
• BAD: "Compare products and select the best one"
• GOOD: "Compare two laptops and select the one with more RAM under $1000"
• BAD: "Search for headphones and add to cart"
• GOOD: "Search for wireless headphones under $200 with 4+ star rating and add the first result to cart"
Step detail requirements (FOCUS ON ACTIONS, NOT VERIFICATION):
• Specific navigation actions (e.g., "Navigate to the homepage")
• Clear element interactions (e.g., "Click the search button in the header")
• Precise data entry (e.g., "Type 'wireless headphones' in the search field")
• Selection actions (e.g., "Select 'Blue' from the color dropdown")
• Page transitions (e.g., "Click on the product image to open details page")
AVOID these types of steps:
• Verification steps (e.g., "Verify the page loaded")
• Validation steps (e.g., "Validate the price is correct")
• Confirmation steps (e.g., "Ensure the button is visible")
Return JSON format:
{{"tasks": [{{"id": "task_1", "name": "...",
"description": "...", "steps": ["..."]}}]}}
"""

# =============================================================================
# 2. INTERFACE DESIGN
# =============================================================================

# Figure 16: Interface Design
PROMPT_INTERFACE_DESIGN = """
You are a software architect. Design comprehensive interfaces for both user tasks AND page functionality.
Website Seed: {website_seed}
User Tasks: {tasks_json}
Data Models: {data_models_json}
Website Pages and Functions: {pages_info}

IMPORTANT REQUIREMENTS:
1. Design USER-FACING interfaces that will be directly called from UI
2. This is for SINGLE-USER agent training - NO userId, sessionId parameters
3. System state (cart, session) should be managed internally, not passed as parameters

CRITICAL: Design interfaces for TWO purposes:
A. TASK EXECUTION INTERFACES - For user tasks:
• What information must be shown BEFORE the user can act (display interfaces)
• What action the user performs (action interfaces)
• What feedback/results need to be shown AFTER the action (result interfaces)

B. PAGE FUNCTIONALITY INTERFACES - For each page's primary_functions:
• Review EVERY primary_function in the Website Pages list
• Ensure there's an interface to support EACH function
• Examples: "Navigate to featured product categories" → needs getCategories()

Additional requirements:
• Interfaces should handle complete operations (e.g., addToCart handles cart creation if needed)
• Do NOT create unnecessary CRUD, but DO create interfaces needed for page display
• For interfaces that get data for display, return user-friendly fields

Return JSON format:
{{
"interfaces": [{{"name": "addToCart",
"description": "Add a product to cart",
"parameters": [{{"name": "productId", "type": "string"}}],
"returns": {{"type": "object",
"properties": {{"success": {{"type": "boolean"}}}}}},
"relatedTasks": ["task_1"]}}],
"helperFunctions": [{{"name": "_getOrCreateCart",
"description": "Internal helper", "visibility": "private"}}]
}}
"""

# Figure 17: Interface Wrapping
PROMPT_INTERFACE_WRAPPING = """
You are a software architect analyzing interface parameters for a {website_type}.
Your task: Identify parameters that should be hidden from user-facing interfaces and generate wrapped versions.
ORIGINAL INTERFACES: {original_interfaces_json}
EXISTING DATA MODELS: {data_models_json}

PARAMETER CLASSIFICATION RULES:
1. SYSTEM-MANAGED PARAMETERS (should be hidden):
• User identity: userId, guestId, sessionId, currentUser
• System context: cartId, deviceId, timestamp, requestId
• Authentication: authToken, userRole, permissions, isAuthenticated
• Environment: locale, timezone, region, currency

2. USER-PROVIDED PARAMETERS (should remain exposed):
• Business data: productId, quantity, rating, comment
• User selections: selectedSize, color, filters
• User input: searchQuery, address, paymentDetails

ANALYSIS CRITERIA:
• Ask: "Would a user type this value into a form or select it from a UI?"
• If YES → Keep as parameter (user-provided)
• If NO → Hide and manage through state (system-managed)

EXAMPLE TRANSFORMATION:
Original: addToCart(userId, guestId, productId, quantity, selectedSize)
Wrapped: addToCart(productId, quantity, selectedSize)
State Needed: UserSession with currentUserId/currentGuestId

Return JSON format:
{{
"wrapped_interfaces": [{{"name": "addToCart",
"parameters": [{{"name": "productId", "type": "string"}}]}}],
"state_data_models": [{{"name": "UserSession",
"fields": [{{"name": "currentUserId", "type": "string"}}]}}],
"implementation_mapping": [{{"wrapped_function": "addToCart",
"parameter_mapping": {{"userId": "_getSession().currentUserId"}}}}]
}}
"""

# =============================================================================
# 3. ARCHITECTURE DESIGN
# =============================================================================

# Figure 18: Architecture Design
PROMPT_ARCHITECTURE_DESIGN = """
You are a web architect. Design complete website architecture based on user tasks and interfaces.
Website Seed: {website_seed}
User Tasks: {task_summary_json}
Primary Architecture (initial design): {primary_arch_json}
Available Interfaces: {interface_summary_json}
Data Models: {data_summary_json}

IMPORTANT:
• This is for SINGLE-USER agent training - NO authentication/login pages needed
• The interfaces provided are USER-FACING interfaces (no userId/sessionId parameters)
• System state is managed automatically through localStorage

Design Requirements:
1. Use EXACTLY the pages from primary architecture - do not add or remove pages
2. Assign appropriate interfaces to each page based on functionality
3. Use URL parameters for navigation (NOT localStorage for page data)
4. Define incoming parameters (what parameters the page accepts)
5. Define outgoing connections (what pages this page navigates to)
6. Specify access methods for each page
7. Design header and footer navigation links

Access Method Guidelines:
• "navigation": Accessible through header/footer navigation
• "url_param": Accessible through URL parameters from other pages
• "direct_link": Accessible through direct links in content
• "form_submission": Accessible after form submission

Return JSON format:
{{
"all_pages": [{{"name": "Home", "filename": "index.html"}}],
"pages": [{{"name": "Home", "filename": "index.html",
"assigned_interfaces": ["searchProducts"],
"incoming_params": [],
"outgoing_connections": [{{"target": "product.html",
"params": {{"id": "productId"}}}}],
"access_methods": [{{"type": "navigation"}}]}}],
"header_links": [{{"text": "Home", "url": "index.html"}}]
}}
"""

# =============================================================================
# 4. PAGE DESIGN
# =============================================================================

# Figure 19: Page Functionality Design
PROMPT_PAGE_FUNCTIONALITY = """
You are a senior web functional designer. Design the functional aspects and workflows of a webpage.
Website Seed: {website_seed}
Page Architecture: {page_spec_json}
Available Data Models: {data_dict_json}
Assigned Interfaces for This Page: {interface_details_json}
Navigation Information: {navigation_info}

DESIGN REQUIREMENTS:
1. Create an engaging, specific page title
2. Write a rich, detailed description of the page
3. Design core features based on the assigned interfaces
4. Define user workflows that utilize the interfaces
5. Specify user interactions (clicks, forms, navigation)
6. Describe state logic using URL parameters (NOT localStorage)
7. Create functional components that use the interfaces

IMPORTANT GUIDELINES:
• Use ONLY the assigned interfaces for this page
• Navigation uses URL parameters (e.g., product.html?id=123)
• Focus on functionality, not visual appearance
• Components should be functional, not presentational
• Each component should have clear data binding and event handlers
• Output should not involve any static data or hardcoded values

Return JSON format:
{{
"title": "Page title", "description": "Page description",
"page_functionality": {{
"core_features": ["Feature 1"],
"user_workflows": ["Workflow step"],
"interactions": ["Click action"],
"state_logic": "URL parameter handling"
}},
"components": [{{"id": "search-form", "type": "search-form",
"functionality": "Handles product search",
"data_binding": ["Product"],
"event_handlers": ["onSubmit"]}}]
}}
"""

# Figure 20: Design Image Analysis
PROMPT_DESIGN_ANALYSIS = """
You are a senior UI/UX design analyst. Analyze the provided design image to extract all visual characteristics.
Website Seed: {website_seed}

ANALYSIS TASKS:
1. Visual Features Analysis:
• Identify overall visual style (modern, minimalist, vibrant, corporate, etc.)
• Describe visual hierarchy and focal points
• Note use of whitespace and visual breathing room
2. Color Scheme Extraction:
• Primary colors (main brand colors)
• Secondary colors (supporting colors)
• Accent colors (for CTAs, highlights)
• Neutral colors (backgrounds, text, borders)
• Provide exact hex color values
3. Layout Characteristics:
• Grid system (12-column, custom, etc.)
• Layout patterns (sidebar, centered, full-width)
• Section organization and alignment principles
4. UI Patterns: Button styles, card designs, form elements, navigation patterns
5. Typography: Font families, size hierarchy, font weights, line heights
6. Spacing System: Base unit, padding/margin patterns, component spacing
7. Interaction Hints: Hover states, transitions, animation suggestions

Return JSON format:
{{
"visual_features": {{"overall_style": "modern minimalist"}},
"color_scheme": {{"primary": ["#hex"], "accent": ["#hex"]}},
"layout_characteristics": {{"grid_system": "12-column"}},
"ui_patterns": [{{"pattern_type": "button",
"characteristics": {{"shape": "rounded"}}}}],
"typography": {{"font_families": {{"heading": "Inter"}}}},
"spacing_system": {{"base_unit": "8px"}}
}}
"""

# Figure 21: Layout Design
PROMPT_LAYOUT_DESIGN = """
You are a senior UI/UX designer. Create a thoughtful, detailed layout for existing components.
DESIGN DNA (extracted from design image):
• Visual Style: {visual_style}
• Grid System: {grid_system}
• Layout Pattern: {layout_pattern}
• Spacing System: {spacing_system_json}
PAGE CONTEXT: Website Seed: {website_seed}, Page: {page_name}
Components to Layout: {components_list}

STEP 1: Choose Layout Strategy Combination
For each dimension, provide reasoning and make a choice:
1. Content Arrangement: linear-flow, grid-based, asymmetric, centered-focus, masonry, split-screen, sidebar-content, magazine-layout
2. Component Grouping: functional-clusters, visual-zones, priority-based, workflow-aligned, data-centric
3. Space Allocation: equal-distribution, primary-focus, golden-ratio, thirds-rule, flexible-grid
4. Content Density: spacious, balanced, compact, variable
5. Visual Flow: top-down, z-pattern, f-pattern, circular, focal-center

STEP 2: Describe each component's layout using natural language (position, size, relationships)
STEP 3: Describe overall layout picture

Return JSON format:
{{
"chosen_strategies": {{"content_arrangement": {{"reasoning": "...",
"choice": "grid-based"}}}},
"overall_layout_description": "Description of full layout",
"component_layouts": [{{"id": "search-form",
"layout_narrative": "Position and size description",
"visual_prominence": "primary"}}]
}}
"""

# =============================================================================
# 5. PAGE GENERATION (HTML/CSS)
# =============================================================================

# Figure 22: Page Framework Generation
PROMPT_FRAMEWORK_GENERATION = """
You are a senior web developer. Analyze the provided design image and generate a complete HTML framework with header and footer that matches the visual style.
Website Seed: {website_seed}
Header Navigation Links: {header_links_json}
Footer Links: {footer_links_json}
Design Analysis Context: {design_context}

Requirements:
1. ANALYZE THE DESIGN IMAGE to extract: visual style, color palette, typography, layout patterns, spacing
2. Create a complete HTML framework matching the design (reusable for all pages)
3. Only include header, footer, and main content area (id="content")
4. Header matching the design's header style with provided navigation links
5. Footer matching the design's footer style with provided footer links
6. Modern, semantic HTML5 structure

CSS Requirements:
• Extract exact colors from the design image
• Match typography from the design
• Replicate spacing and sizing
• Create CSS variables for the design system

CRITICAL:
• Use English only
• Do NOT include interactive elements without corresponding links
• SVG files are not allowed in the framework

Return JSON format:
{{
"framework_html": "HTML with header/footer",
"framework_css": "CSS replicating the design"
}}
"""

# Figure 23: HTML Page Generation
PROMPT_HTML_GENERATION = """
You are a senior web developer. Generate the main content HTML for a {website_type} website page with UI JavaScript.
Page Information: {page_design_json}
Navigation Information: {page_architecture_json}
Framework HTML Reference (DO NOT RE-GENERATE HEADER/FOOTER): {framework_html}
Data Dictionary: {data_dict_json}
Page-Specific SDK Interfaces: {page_interfaces_json}

REQUIREMENTS:
1. Generate the content that will go inside the <main id="content"> section.
2. CRITICAL: Implement ALL "outgoing_connections" as visible UI elements (e.g., <button>, <a href="...">, or clickable cards). 
3. If the architecture says this page connects to "add-task.html", you MUST provide a button or link to that page.
4. Call interfaces as WebsiteSDK.functionName() - they are SYNCHRONOUS.
5. Handle incoming_params: Extract URL parameters this page expects.
6. Add data attributes: data-populate, data-action, data-component.

UI JAVASCRIPT REQUIREMENTS:
1. Initialize page when DOM is ready.
2. Extract URL parameters for incoming_params.
3. Implement navigation logic for outgoing_connections - use window.location.href for page transitions.
4. Set up event listeners based on data-action attributes.

CRITICAL: 
- Use only relative .html URLs for internal navigation.
- Ensure the UI makes it obvious HOW a user can navigate to the next page in the flow.
- Call ONLY the provided SDK interfaces from the "Page-Specific SDK Interfaces" list. 
- DO NOT assume any getters, summaries, or other methods exist if they are not explicitly listed.
- If a method you need (like a summary) is missing, simplify the UI or display placeholders rather than creating hypothetical calls.

Return: {{"html_content": "The HTML content for the main section, including UI scripts"}}
"""

# Figure 24: CSS Page Generation
PROMPT_CSS_GENERATION = """
You are a senior web developer. Generate CSS styles for the page based on its HTML structure.
Page Design: {page_design_json}
Page Layout: {page_layout_json}
Design Analysis: {design_analysis_json}
Framework CSS (build upon this): {framework_css}
Generated HTML (style this content): {html_content}

Requirements:
1. Include complete framework CSS - no abbreviations
2. Style the content area and page-specific components
3. Follow the design analysis color scheme and typography
4. Implement the layout specifications (grid, spacing, etc.)
5. Ensure responsive design with proper breakpoints
6. Use CSS variables defined in framework CSS
7. Add hover states and transitions for interactive elements
8. Use modern CSS features (flexbox, grid, custom properties)

CRITICAL: Put this at the VERY TOP of css_content:
[hidden] {{ display: none !important; }}

Return: {{"css_content": "Complete CSS including framework and page-specific styles"}}
"""

# =============================================================================
# 6. DATA GENERATION
# =============================================================================

# Figure 25: Data Generation
PROMPT_DATA_GENERATION = """
You are a data generator specializing in realistic website data. Generate comprehensive, realistic data based on the EXACT data dictionary specifications.
Website Seed: {website_seed}
User Tasks Context: {tasks_json}
Data Dictionary Structure: {data_types_info_json}

CRITICAL CONSTRAINTS:
1. Use data_type_name as JSON key: Use the exact value from "data_type_name" field
2. Use EXACT field names: Only fields defined in fields dictionary
3. Follow field types: string, number, boolean, array, datetime as specified
4. Intelligent Volume Decision: Based on generation_type:
• "many": Generate substantial amount approaching max_items
• "few": Generate small representative set (20-30% of max_items)
5. No extra fields: Do NOT add fields not in the dictionary

IMAGE URL REQUIREMENTS: Use ONLY real, working image services:
• Unsplash: https://images.unsplash.com/photo-[ID]?w=800&h=600
• Picsum: https://picsum.photos/800/600?random=[1-1000]

DATA QUALITY: Generate realistic, diverse content appropriate for the website seed. Ensure data relationships are logical and consistent.

Return JSON format:
{{
"static_data": {{
    "products": [{{"field1": "value"}}],
    "categories": [{{"id": "cat_1", "name": "Category"}}]
}}
}}
"""

# =============================================================================
# 7. BACKEND GENERATION
# =============================================================================

# Figure 26: Backend Implementation Generation
PROMPT_BACKEND_IMPLEMENTATION = """
You are an expert JavaScript developer. Generate a complete business logic implementation.
Website Seed: {website_seed}
Tasks: {tasks_json}
Data Models: {data_models_json}
Interfaces: {interfaces_json}

REQUIREMENTS:
1. Implement ALL core interfaces specified
2. Add helper functions as needed (prefix with _ for private)
3. Use localStorage for ALL data persistence (browser-compatible)
4. NO DOM operations, NO window/document references (except localStorage)
5. Must work in both browser and Node.js environments
6. All data must be JSON serializable for localStorage
7. Implement interfaces with positional arguments only

STRUCTURE:
const localStorage = (function() {{ ... }})(); // polyfill
class BusinessLogic {{
constructor() {{ this._initStorage(); }}
_initStorage() {{ /* init localStorage tables */ }}
_getFromStorage(key) {{ /* retrieve data */ }}
_saveToStorage(key, data) {{ /* persist data */ }}
addToCart(productId, quantity) {{ /* implementation */ }}
}}
if (typeof window !== 'undefined') {{
  window.WebsiteSDK = new BusinessLogic();
}}
module.exports = BusinessLogic;

Return: {{"code": "javascript code here"}}
"""

# Figure 27: Backend Test Generation
PROMPT_BACKEND_TEST = """
You are an expert test engineer. Generate flow-based integration tests for the business logic.
Website Seed: {website_seed}
Tasks: {tasks_json}
Interfaces: {interfaces_json}
Generated Data: {generated_data_json}

CRITICAL REQUIREMENTS:
1. Use Generated Data ONLY in setupTestData() for initial localStorage population
2. NEVER hardcode expected return values - always extract from actual API responses
3. Chain API calls properly: Call API, capture response, extract needed values for next calls
4. Test complete user flows, not individual functions
5. Focus on happy path (successful scenarios)
6. Must run in Node.js environment
7. Test ALL tasks provided

CORRECT Flow Testing Example:
const addResult = this.logic.addToCart(userId, productId, 2);
const actualCartId = addResult.cartId; // Extract from response
const cartData = this.logic.getCart(actualCartId); // Use actual ID
this.assert(cartData.total > 0, 'Total should be positive');

Return: {{"code": "javascript test code"}}
"""

# =============================================================================
# 8. EVALUATOR GENERATION
# =============================================================================

# Figure 28: Evaluator Generation
PROMPT_EVALUATOR_GENERATION = """
You are a QA engineer. Create evaluators to check if users complete tasks successfully.
Website Seed: {website_seed}
Tasks to evaluate: {tasks_json}
Cross-Page States Structure: {cross_page_states_json}
Generated Data Structure: {data_structure_json}

For each task, create an evaluator that:
• Uses cross-page states stored in localStorage to determine completion
• Uses data structure knowledge to create precise validation logic
• References exact field names and data types from the data structure
• Provides clear evaluation criteria and logic
• Uses JavaScript logic to check task completion status

Guidelines:
• Use localStorage.getItem() to access both cross-page states and static data
• Parse JSON data when retrieving complex objects from localStorage
• Check for null/undefined values before accessing object properties
• Use realistic validation logic based on the actual data structure

Return JSON format:
{{
"evaluators": [{{"task_id": "task_1", "name": "Evaluator Name",
"description": "What this evaluator checks",
"localStorage_variables": ["selectedProductId", "products"],
"evaluation_logic": "const products = JSON.parse(...); ..."}}]
}}
"""

# =============================================================================
# 9. INSTRUMENTATION
# =============================================================================

# Figure 29: Instrumentation Analysis
PROMPT_INSTRUMENTATION_ANALYSIS = """
You are analyzing JavaScript business logic to determine what instrumentation variables are needed to evaluate task completion.
TASKS TO EVALUATE: {tasks_json}
CURRENT BUSINESS LOGIC: {code_snippet}
EXISTING LOCALSTORAGE VARIABLES: {existing_storage_vars_json}
DATA STORAGE KEYS: {storage_keys_json}

ANALYSIS REQUIREMENTS: For each task, determine:
1. What operations must occur for the task to be considered complete?
2. Can we use existing localStorage variables to determine completion?
3. If NOT, what new instrumentation variables are needed?

INSTRUMENTATION GUIDELINES:
• Track ALL critical intermediate milestones, even if the final result is observable in localStorage.
• Add variables to capture the USER'S ACTIONS and DECISION POINTS (e.g., filters applied, tabs switched, search performed).
• Use naming convention: taskN_actionDescription (e.g., task1_sortPriceApplied, task2_detailViewed).
• Aim for 2-4 instrumentation variables PER task to ensure high-fidelity trajectory tracking.
• Specify which function should set the variable and under what condition.

Return JSON:
{{
"requirements": [{{
  "task_id": "task_1",
  "needs_instrumentation": true,
  "required_variables": [
    {{
      "variable_name": "task1_sortApplied",
      "set_in_function": "getPurchaseOrders",
      "set_condition": "When sortBy is totalValue_desc"
    }},
    {{
      "variable_name": "task1_approved",
      "set_in_function": "approvePurchaseOrder",
      "set_condition": "After successful approval"
    }}
  ]
}}]
}}
"""

# Figure 30: Instrumentation Code Generation
PROMPT_INSTRUMENTATION_CODE = """
You are adding instrumentation variables to JavaScript business logic for task completion tracking.
ORIGINAL CODE: {original_code}
INSTRUMENTATION SPECIFICATIONS: {instrumentation_specs_json}

INSTRUCTIONS: For each instrumentation variable:
1. Find the specified function in the code
2. Add code to set both localStorage AND window.__instrumentation based on set_condition
3. Use the following pattern:
   try {{
     localStorage.setItem('VARIABLE_NAME', 'VALUE');
     window.__instrumentation = window.__instrumentation || {{}};
     window.__instrumentation['VARIABLE_NAME'] = 'VALUE';
   }} catch(e) {{}}
4. Use the exact variable_name and value_to_set from specifications

CRITICAL REQUIREMENTS:
• DO NOT change any original functionality
• DO NOT modify function signatures or return values
• Instrumentation code must be wrapped in try-catch
• REQUIRED: Update window.__instrumentation for Agent visibility
• Preserve all existing code structure and comments
• Place instrumentation BEFORE the return statement

Return: Complete instrumented business_logic.js code
"""

# Figure 31: Instrumentation Evaluator Generation
PROMPT_INSTRUMENTATION_EVALUATOR = """
You are generating evaluators to check if users completed tasks successfully.
TASKS: {tasks_json}
INSTRUMENTATION VARIABLES AVAILABLE: {var_mapping_json}
BUSINESS LOGIC IMPLEMENTATION: {business_logic_code}
WEBSITE DATA: {website_data_json}

INSTRUCTIONS: For each task, create an evaluator based on the instrumentation plan:
Case 1: Tasks with needs_instrumentation=true
• Use the instrumentation_variables specific to that task
• Validate the variable values match expected values

Case 2: Tasks with needs_instrumentation=false
• Use the existing_variables to infer task completion
• Check the ACTUAL data structure from the business logic implementation

All evaluators must:
• Check if the variables exist in localStorage
• Use the EXACT data structure from the business logic implementation
• Return true if the task is completed, false otherwise

Return JSON:
{{
"evaluators": [{{"task_id": "task_1", "name": "...",
"localStorage_variables": ["var1", "var2"],
"evaluation_logic": "// JavaScript returning boolean"}}]
}}
"""

PROMPT_VISUAL_VALIDATION = """
You are a Senior UI/UX QA Engineer. Your task is to evaluate a generated web page based on a screenshot and the original requirement.

### Input:
- **Seed/Topic**: {seed}
- **Page Name**: {page_name}
- **Page Description**: {page_description}

### Evaluation Criteria:
1. **Visual Richness**: Does it look like a real website or just a bare skeleton? Is there consistent styling?
2. **Component Presence**: Are the expected components (e.g., header, forms, calculation results, buttons) visible and correctly placed?
3. **Layout Integrity**: Are there any obvious layout breaks, overlapping elements, or off-screen content?
4. **Professionalism**: Does the design feel premium or amateurish?

### Response Format:
Return a JSON object:
{{
    "score": 0-10,
    "pass": boolean,
    "feedback": "Detailed feedback describing visual issues or praise",
    "visual_bugs": ["bug 1", "bug 2"]
}}
"""
