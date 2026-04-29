# User Input

[<arguments>]

# Instructions

You must first consider user input before proceseding (if given).

Identity new code changes made in this branch and compare them with the specification (tasks and specs).

Create a report of **recent** (commits that not exist in the immediate ancestor branch) code changes and find relationship between affected code and the tasks.

Focus on the difference between spacification and implementation. If there are new changes in code that are not included in the specification - suggest an task-editing remediation action. If the code is not covered by specification at all, suggest a reverse-engineering remediation action.

Put the report in a file named `gap-<number>.md` in the `.fvc` folder. No note overwrite existing files, generate a new number.

Paths, relative the the project root, to search for specs and tasks definition:
- `specs`
- `docs`

Do not changes the code.

