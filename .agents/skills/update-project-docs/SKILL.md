---
name: update-project-docs
description: "Trigger this skill to update the AI_ONBOARDING.md and README.md files when significant architectural, deployment, or structural changes are made to the project."
---

# Update Project Documentation (AI_ONBOARDING.md)

This skill enables the agent to automatically keep the project documentation up to date.

## When to use this skill
- When the user explicitly asks to "update the docs" or "belgeleri güncelle".
- When you (the agent) have made significant changes to the project's architecture, dependencies (e.g., adding a new backend tool), deployment process, or directory structure.

## Instructions
1. Review the recent changes made to the project or the user's explicit instructions.
2. Read the current contents of `AI_ONBOARDING.md` and `README.md` (if it exists).
3. Identify which sections of the documentation are now outdated. For example:
   - Did the deployment commands change?
   - Was a new table added to the Supabase database?
   - Did the frontend technology stack change?
4. Use your code editing tools (`replace_file_content` or `multi_replace_file_content`) to update the affected sections in `AI_ONBOARDING.md`.
5. Keep the language in Turkish, as the original documentation is in Turkish.
6. Ensure that the core architectural rules (like "No Streamlit allowed") are preserved unless they have been explicitly removed by the user.
7. Notify the user that the documentation has been updated successfully.
