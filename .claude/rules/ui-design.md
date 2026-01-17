# UI Design Rules

Based on Jakob Nielsen's 10 Usability Heuristics for User Interface Design.

## 1. Visibility of System Status

Always keep users informed about what is happening through appropriate feedback.

- Show loading states for async operations (spinners, progress bars, skeleton screens)
- Provide immediate visual feedback on user actions (button press states, form validation)
- Display clear success/error confirmations after operations complete
- Show progress indicators for multi-step processes
- Indicate current location in navigation (active states, breadcrumbs)

## 2. Match Between System and Real World

Use language and concepts familiar to users, not technical jargon.

- Use plain language labels, not internal/technical terminology
- Follow real-world conventions (e.g., shopping cart icon for e-commerce)
- Organize information in logical, natural order
- Use familiar icons and metaphors
- Match control layouts to physical counterparts when applicable

## 3. User Control and Freedom

Provide clear escape routes from unwanted states.

- Always include visible cancel/close buttons
- Support undo/redo for destructive actions
- Allow users to go back in multi-step flows
- Provide clear navigation to exit current context
- Never trap users in modal dialogs without exit options

## 4. Consistency and Standards

Follow platform conventions and maintain internal consistency.

- Use consistent terminology throughout the interface
- Maintain uniform visual styling (colors, spacing, typography)
- Follow platform UI conventions (iOS, Android, web standards)
- Keep interaction patterns consistent across similar features
- Use standard icons for common actions (save, delete, edit, search)

## 5. Error Prevention

Design to prevent errors before they occur.

- Use confirmation dialogs for destructive actions
- Provide smart defaults and constraints on inputs
- Disable invalid options rather than showing errors after selection
- Use input masks and validation to guide correct data entry
- Show inline validation before form submission

## 6. Recognition Rather Than Recall

Minimize memory load by making options and actions visible.

- Show recently used items and suggestions
- Use descriptive labels, not cryptic codes
- Provide visual cues and context for actions
- Display helpful placeholder text in inputs
- Keep important information visible, don't hide behind menus

## 7. Flexibility and Efficiency of Use

Support both novice and expert users.

- Provide keyboard shortcuts for common actions
- Support touch gestures where appropriate
- Allow customization of frequently used features
- Offer both simple and advanced modes when needed
- Enable bulk operations for power users

## 8. Aesthetic and Minimalist Design

Include only essential information and elements.

- Remove decorative elements that don't serve a purpose
- Prioritize primary actions, de-emphasize secondary ones
- Use whitespace effectively to reduce visual noise
- Show only relevant information for the current task
- Avoid cluttered layouts; group related elements

## 9. Help Users Recover from Errors

Make error messages clear, specific, and actionable.

- Use plain language, not error codes
- Clearly identify what went wrong
- Suggest specific steps to fix the problem
- Use appropriate visual indicators (color, icons)
- Place error messages near the source of the error

## 10. Help and Documentation

Provide accessible, contextual help when needed.

- Include tooltips for complex features
- Provide inline help text for form fields
- Make documentation searchable
- Offer contextual help relevant to current task
- Use progressive disclosure for complex features

---

## Implementation Checklist

When building or reviewing UI components, verify:

- [ ] Loading and error states are handled
- [ ] User can always navigate back or cancel
- [ ] Labels use plain language
- [ ] Visual styling is consistent with existing patterns
- [ ] Destructive actions require confirmation
- [ ] Form validation is inline and helpful
- [ ] Error messages explain how to fix issues
- [ ] Primary actions are visually prominent
- [ ] Interface works without requiring memorization
