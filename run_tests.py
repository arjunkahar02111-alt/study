"""
Test Runner for Smart Study Planner
Executes all 14 Criterion B Test Plan cases and formats the results
directly into a Markdown and console table ready for Criterion D (Test Results).
"""

import unittest
import sys
from test_study_planner import SmartStudyPlannerTestCase

TEST_CASES_METADATA = [
    {
        "method": "test_01_add_task",
        "feature": "Add task",
        "test_case": "Enter valid task details",
        "expected": "Task should be saved in the database",
    },
    {
        "method": "test_02_input_validation_empty_fields",
        "feature": "Input validation",
        "test_case": "Submit the form with empty required fields",
        "expected": "System should display an error message",
    },
    {
        "method": "test_03_difficulty_validation",
        "feature": "Difficulty validation",
        "test_case": "Enter a difficulty value outside 1–5",
        "expected": "System should reject the invalid value",
    },
    {
        "method": "test_04_importance_validation",
        "feature": "Importance validation",
        "test_case": "Enter an importance value outside 1–5",
        "expected": "System should reject the invalid value",
    },
    {
        "method": "test_05_priority_calculation",
        "feature": "Priority calculation",
        "test_case": "Enter known task values",
        "expected": "System should calculate the correct priority score",
    },
    {
        "method": "test_06_task_sorting",
        "feature": "Task sorting",
        "test_case": "Add tasks with different priority scores",
        "expected": "Tasks should be displayed in descending priority order",
    },
    {
        "method": "test_07_edit_task",
        "feature": "Edit task",
        "test_case": "Change the deadline of an existing task",
        "expected": "Updated information should be saved and priority recalculated",
    },
    {
        "method": "test_08_delete_task",
        "feature": "Delete task",
        "test_case": "Delete an existing task",
        "expected": "Task should be removed from the database",
    },
    {
        "method": "test_09_complete_task",
        "feature": "Complete task",
        "test_case": "Mark a pending task as completed",
        "expected": "Task status should change to completed",
    },
    {
        "method": "test_10_overdue_tasks",
        "feature": "Overdue tasks",
        "test_case": "Add a task with a past deadline",
        "expected": "Task should be labelled as overdue",
    },
    {
        "method": "test_11_upcoming_deadlines",
        "feature": "Upcoming deadlines",
        "test_case": "Add tasks with approaching deadlines",
        "expected": "Upcoming tasks should be displayed clearly",
    },
    {
        "method": "test_12_data_storage",
        "feature": "Data storage",
        "test_case": "Refresh the website after adding tasks",
        "expected": "Saved tasks should remain available",
    },
    {
        "method": "test_13_study_plan",
        "feature": "Study plan",
        "test_case": "Add multiple pending tasks",
        "expected": "An organized study plan should be generated",
    },
    {
        "method": "test_14_user_interface",
        "feature": "User interface",
        "test_case": "Navigate between the dashboard, task form, and study plan",
        "expected": "Pages should work correctly and be easy to navigate",
    },
]


def run_all_tests():
    print("=" * 80)
    print("RUNNING CRITERION B TEST PLAN SUITE FOR SMART STUDY PLANNER")
    print("=" * 80)

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()

    for item in TEST_CASES_METADATA:
        suite.addTest(SmartStudyPlannerTestCase(item["method"]))

    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)

    failed_methods = [test.id().split(".")[-1] for test, _ in result.failures + result.errors]

    print("\n" + "=" * 80)
    print("CRITERION D: TEST RESULTS TABLE (Copyable Markdown)")
    print("=" * 80 + "\n")

    md_table = []
    header = "| # | Feature | Test Case | Expected Outcome | Actual Outcome | Fixes Needed |"
    divider = "| :--- | :--- | :--- | :--- | :--- | :--- |"
    md_table.append(header)
    md_table.append(divider)

    for idx, item in enumerate(TEST_CASES_METADATA, 1):
        if item["method"] in failed_methods:
            actual = "FAILED - Error encountered"
            fix = "Review logic and retest"
        else:
            actual = "PASSED - Verified as expected"
            fix = "None - Functioning as expected"

        row = f"| {idx} | {item['feature']} | {item['test_case']} | {item['expected']} | {actual} | {fix} |"
        md_table.append(row)

    table_output = "\n".join(md_table)
    print(table_output)

    print("\n" + "=" * 80)
    print(f"Total Tests Run: {result.testsRun}")
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failed: {len(result.failures) + len(result.errors)}")
    print("=" * 80)

    return len(result.failures) + len(result.errors) == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
