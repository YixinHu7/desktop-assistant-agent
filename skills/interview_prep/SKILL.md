---
name: interview_prep
description: Use this skill when the user asks to prepare for an interview, create an interview checklist, practice behavioral questions, prepare STAR stories, or organize interview materials.
---

# Interview Prep Skill

## Purpose

Use this skill to help the user prepare for interviews in a structured and practical way.

## When to Use

Use this skill when the user asks to:

- prepare for an interview
- create an interview prep checklist
- practice behavioral questions
- prepare STAR stories
- organize interview materials
- generate mock interview questions
- plan what to review before an interview

Do not use this skill for general career advice that does not involve concrete interview preparation.

## Recommended Process

1. Identify the type of interview if provided:
   - product management
   - software engineering
   - AI/ML
   - data science
   - behavioral
   - general internship

2. If the role/company is unknown, create a general but practical preparation plan.

3. Build the response around useful sections:
   - Key topics to review
   - Common interview questions
   - STAR story preparation
   - Questions to ask the interviewer
   - Materials to prepare
   - Final-day checklist

4. If the user asks to save the result, call `create_note`.

5. If the user asks to remember interview preferences or long-term goals, use memory tools if available.

## STAR Story Guidance

For behavioral interviews, help structure answers using:

- Situation
- Task
- Action
- Result
- Reflection / learning

## Output Style

For a normal answer, use:

1. Quick preparation plan
2. Practice questions
3. STAR story prompts
4. Final checklist

For a saved note, use a clear title such as:

`Interview Prep Plan`

## Rules

- Keep advice practical and actionable.
- Do not invent company-specific facts if the company is not provided.
- If role/company information is missing, state assumptions clearly.
- Prefer concise checklists over long paragraphs.