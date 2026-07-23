# Scenario: multi-tenant approval workflow

Design requirements for a web application:

- Users submit documents for approval within their organization.
- Reviewers can approve or request changes; administrators can act for any team.
- A background job extracts document metadata and sends notifications.
- The UI uses optimistic updates and caches document lists for five minutes.
- Customers may configure webhooks for approval events.
- Documents can be shared by URL with external collaborators.
- Every important action should be logged.
- The service must remain usable during rolling deployments.

Do not invent authorization or consistency behavior. Identify material questions that must be resolved before a technical plan is executable.
