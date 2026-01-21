import json
from ..interfaces import ISpecGenerator, ILLMProvider
from ..domain import WebsiteSpec, Task, PageSpec, InterfaceDef, DataModel
from ..prompts.library import PROMPT_INTERFACE_DESIGN, PROMPT_DATA_GENERATION, PROMPT_TASK_GENERATION

class LLMSpecGenerator(ISpecGenerator):
    def __init__(self, llm: ILLMProvider):
        self.llm = llm

    def generate(self, seed: str) -> WebsiteSpec:
        """
        Generates the Unified Specification using Official InfiniteWeb Prompts.
        Strategy:
        1. Tasks (Seeds)
        2. Schema (Data Models & Pages) - Prerequisites for Interface Design
        3. Interfaces (Figure 16) - Requires Tasks, Models, Pages
        """
        print(f"🤖 [LLM] Generating Tasks for '{seed}'...")
        tasks, instruction = self._gen_tasks(seed)
        
        print(f"🤖 [LLM] Generating Data Models & Page Structure...")
        models, pages = self._gen_schema(seed, tasks)
        
        print(f"🤖 [LLM] Designing Unified Interfaces (Official Prompt)...")
        interfaces = self._gen_interfaces(seed, tasks, models, pages)
        
        return WebsiteSpec(
            seed=seed,
            task_instruction=instruction,
            tasks=tasks,
            interfaces=interfaces,
            data_models=models,
            pages=pages
        )

    def _gen_tasks(self, seed: str):
        prompt = PROMPT_TASK_GENERATION.format(website_seed=seed)
        
        data = self._parse(self.llm.prompt_json(prompt))
        tasks = [Task(**self._sanitize(Task, t)) for t in data.get("tasks", [])]
        return tasks, data.get("task_instruction", "Complete tasks")

    def _gen_schema(self, seed: str, tasks: list):
        # Using a prompt adapted from Figure 25/18 to get the base structure needed for Interface Design
        # (Since Figure 16 requires 'data_models' and 'pages' as input)
        tasks_json = json.dumps([t.__dict__ for t in tasks])
        prompt = f"""
        Role: System Architect.
        Seed: "{seed}"
        Tasks: {tasks_json}
        
        Goal: Define the Data Domain and Page Architecture needed to support these tasks.
        
        Output JSON:
        {{
            "data_models": [ {{ "name": "Product", "attributes": {{ "id": "string", "price": "number" }} }} ],
            "pages": [ {{ "name": "Home", "filename": "index.html", "description": "..." }} ]
        }}
        """
        data = self._parse(self.llm.prompt_json(prompt))
        models = [DataModel(**self._sanitize(DataModel, m)) for m in data.get("data_models", [])]
        pages = [PageSpec(**self._sanitize(PageSpec, p)) for p in data.get("pages", [])]
        return models, pages

    def _gen_interfaces(self, seed: str, tasks: list, models: list, pages: list):
        # Prepare inputs for Figure 16
        tasks_json = json.dumps([t.__dict__ for t in tasks])
        data_models_json = json.dumps([m.__dict__ for m in models])
        pages_info = json.dumps([p.__dict__ for p in pages])
        
        formatted_prompt = PROMPT_INTERFACE_DESIGN.format(
            website_seed=seed,
            tasks_json=tasks_json,
            data_models_json=data_models_json,
            pages_info=pages_info
        )
        
        data = self._parse(self.llm.prompt_json(formatted_prompt))
        return [InterfaceDef(**self._sanitize(InterfaceDef, i)) for i in data.get("interfaces", [])]

    def _parse(self, json_str: str):
        try:
            return json.loads(json_str)
        except:
            return {}
            
    def _sanitize(self, cls, data):
        valid = cls.__annotations__.keys()
        # Robustness fixes
        if "required_stages" in data: data["required_steps"] = data.pop("required_stages")
        clean = {k: v for k, v in data.items() if k in valid}
        # Add defaults
        if cls == Task:
            if "required_steps" not in clean: clean["required_steps"] = []
            if "complexity" not in clean: clean["complexity"] = 1
            if "id" not in clean: clean["id"] = "task_unknown"
            if "description" not in clean: clean["description"] = "No description"
        if cls == PageSpec:
             if "required_interfaces" not in clean: clean["required_interfaces"] = []
             if "description" not in clean: clean["description"] = "Generated page"
             if "name" not in clean: clean["name"] = "Untitled Page"
             if "filename" not in clean: clean["filename"] = f"{clean.get('name', 'page').lower().replace(' ', '_')}.html"
        
        if cls == InterfaceDef:
             if "parameters" not in clean: clean["parameters"] = {}
             if "return_type" not in clean: clean["return_type"] = "void"
             if "description" not in clean: clean["description"] = "No description"
        
        return clean
