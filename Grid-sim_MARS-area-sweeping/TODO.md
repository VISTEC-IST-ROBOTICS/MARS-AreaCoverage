# TODO.md

This document outlines the tasks required to complete the documentation and finalize the implementation of the **Multi-Agent Sweeping Simulator** project.

---

## Documentation Tasks

### 1. **Software Design**
   - [x] **Detect when all agents stop sweeping while the task is incomplete**  
         *Document this in* `docs/architecture.md`. Include an explanation of the detection mechanism and its role in the architecture.

   - [x] **Measure Task Incompleteness**  
         Provide a detailed overview in `docs/architecture.md`. Emphasize how the architecture supports modularity and interchangeability of components to assess task completion status.

   - [ ] **Implement History Sharing Scheme**  
         Document the purpose, design, and flow of the history-sharing mechanism among agents. Ensure to clarify how it enhances coordination and task efficiency.

   - [ ] **Implement Filtering Algorithm**  
         Write about the filtering algorithm's purpose and application in the simulator, highlighting any optimizations or considerations for multi-agent environments.
   - [ ] **Implement Automate spawning and logging**  
   - [ ] **Code Cleanup and Restructuring**  
         Create a summary explaining the restructuring process, including a before-and-after comparison of the codebase. Ensure readability and maintainability are discussed.

---

## Implementation Notes
- Use modularity principles for all new implementations to ensure maintainability.  
- Highlight areas of improvement in code efficiency within documentation where necessary.  
- Align documentation updates with the finalized code changes to maintain accuracy.  

---
