# Gujdoc — Frontend Design

## Product direction

Gujdoc is a calm, trustworthy workspace for turning Gujarati government PDFs into an
answerable personal knowledge base. The interface should feel closer to a well-made
research desk than a chatbot: documents are visible, their processing state is legible,
and every answer points back to its source.

## Visual language

- **Canvas:** warm ivory (`#f7f5ef`) with subtle paper grain and soft card surfaces.
- **Navigation:** ink navy (`#17233b`) sidebar, used as the dependable anchor of the app.
- **Primary accent:** saffron (`#e88d35`) for actions, active states, and document marks.
- **Secondary accent:** teal (`#2b8a83`) for completed/verified states.
- **Typography:** Fraunces for display moments and headings; DM Sans for interface copy.
- **Shape:** 14px card corners, 10px controls, thin blue-grey borders, restrained shadows.
- **Texture:** tiny dot grid in the main workspace and a vertical ruled line motif in the
  sidebar to suggest archival paper without becoming decorative noise.

## Information architecture

1. **Workspace / Ask**
   - Header with workspace name, document count, and account control.
   - Large question composer with scope selector: all documents or one document.
   - Answer panel with status, answer text, and numbered source citations.
   - Suggested prompts to help a new user start.
2. **Documents**
   - Upload dropzone and PDF-only affordance.
   - Filterable document list with filename, size/date metadata, and processing state.
   - Row actions for open details, retry failed processing, and delete.
   - Detail drawer with source metadata and document-scoped question shortcut.
3. **Search**
   - Semantic search input and compact result cards with matched excerpts, page, and
     relevance distance.
4. **Account**
   - Login/register gate, persisted token session, and logout action.

## State and feedback

- `pending` / `processing`: amber status dot, “Preparing text…” label, animated progress
  line, and disabled document-scoped questioning until complete.
- `completed`: teal status dot, “Ready to ask” label, check icon.
- `failed`: coral status dot, clear failure label, visible “Retry processing” action.
- Empty states always explain what to do next; error states display the API message when
  available and never silently fall back.
- Upload uses an optimistic queue row only after the API confirms the document ID.

## Responsive behavior

- Desktop: fixed 250px sidebar + fluid workspace, max content width 1180px.
- Tablet: 210px sidebar and single-column answer/search panels.
- Mobile: collapsible top navigation, stacked cards, full-width composer, compact rows.

## Component architecture

- `AppShell`: auth gate, sidebar, workspace routing, global toast.
- `Sidebar`: navigation, workspace summary, account/logout.
- `AskView`: scope selector, composer, answer/source rendering.
- `DocumentsView`: upload panel, filters, list, document detail drawer.
- `SearchView`: semantic search form and result cards.
- `AuthScreen`: login/register form with field validation.
- `api.ts`: typed Axios client for every backend route.

## Accessibility and interaction

- All controls have visible labels or accessible names.
- Focus states use a high-contrast saffron ring.
- Status is communicated through text and color.
- Destructive deletion requires an inline confirmation step.
- Keyboard users can navigate the sidebar, composer, upload control, and drawers without
  relying on pointer-only interactions.
