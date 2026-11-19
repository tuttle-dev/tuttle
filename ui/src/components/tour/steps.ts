import type { NavigationFilter } from "../shared/NavigationContext";

/**
 * The tour: the basic workflow, then the key settings, shown on the demo data.
 *
 * Steps find what they highlight by `data-*` attributes in the views
 * (`data-section`, `data-field`, `data-tour`, `data-nav`, …), so renaming one
 * of those breaks a step.
 */

/** The demo project the tour follows: an hourly contract, billed monthly from tracked time. */
export const TOUR_PROJECT_TAG = "#emergency";

/** The demo records the tour shows, looked up when it starts. */
export interface TourRecords {
  clientId?: number;
  contractId?: number;
  projectId?: number;
  /** A recent day with time on the project. */
  day?: string;
}

/** Elements to highlight: every match as one area, or with `each` as separate areas. */
export interface TourTarget {
  selector: string;
  each?: boolean;
}

export type Side = "left" | "right" | "above" | "below";

export interface TourStep {
  kind?: "intro" | "outro";
  /** The part of the tour (an index into TOUR_PARTS) and the step's place in it. */
  part?: number;
  node?: number;
  view: string;
  filter?: (records: TourRecords) => NavigationFilter;
  /** What the tour seems to click to get here, when the view stays the same. */
  via?: string;
  targets?: TourTarget[];
  /** Controls to point at: where the user does this themselves. */
  pulses?: string[];
  /** The target the card sits next to, and the sides it may take. */
  anchor?: number;
  sides?: Side[];
  title: string;
  /** "{new}" shows the toolbar's New button. */
  body: string;
}

export const TOUR_PARTS = [
  ["Client", "Contract", "Project", "Time", "Invoice", "Overview"],
  ["Profile", "Region", "Invoicing", "AI"],
];

const NEW_BUTTON = '.view-toolbar [data-tour="toolbar-primary"]';
const settingsTab = (tab: string) => `[data-settings-tab="${tab}"]`;

export const TOUR_STEPS: TourStep[] = [
  {
    kind: "intro", view: "dashboard",
    title: "Welcome to Tuttle",
    body: "The basic workflow and the key settings, shown on example data.",
  },

  // -- The workflow ----------------------------------------------------------
  {
    part: 0, node: 0, view: "clients",
    filter: (r) => ({ clientId: r.clientId, edit: true }),
    targets: [{ selector: '[data-section="Client"]' }], pulses: [NEW_BUTTON], sides: ["left", "below"],
    title: "Add a client",
    body: "Who you work for. Start with {new}",
  },
  {
    part: 0, node: 1, view: "contracts",
    filter: (r) => ({ contractId: r.contractId, edit: true }),
    targets: [{ selector: '[data-section="Pricing"]' }], pulses: [NEW_BUTTON], sides: ["left", "below"],
    title: "Set your rate",
    body: "Rate, VAT and billing cycle. Every invoice uses them.",
  },
  {
    part: 0, node: 2, view: "projects",
    filter: (r) => ({ projectId: r.projectId, edit: true }),
    targets: [{ selector: '[data-field="Tag"]' }, { selector: '[data-section="Contract"]' }],
    pulses: [NEW_BUTTON], anchor: 1, sides: ["left", "below"],
    title: "Create a project",
    body: "Its tag links tracked time to the contract.",
  },
  {
    part: 0, node: 3, view: "timetracking",
    filter: (r) => ({ day: r.day }),
    targets: [{ selector: '[data-tour="time-entry"]' }, { selector: `[data-tag="${TOUR_PROJECT_TAG}"]`, each: true }],
    anchor: 1, sides: ["above", "below"],
    title: "Track your time",
    body: "Use the timer, log hours, or tag events in your calendar.",
  },
  {
    part: 0, node: 4, view: "invoicing",
    filter: (r) => ({ newInvoice: true, projectId: r.projectId }),
    targets: [{ selector: '[data-tour="invoice-project"], [data-tour="invoice-source"]' }], sides: ["right", "left"],
    title: "Invoice tracked time",
    body: "Pick the project and period. Tuttle bills the hours at your rate.",
  },
  {
    part: 0, node: 5, view: "dashboard",
    targets: [{ selector: '[data-tour="overview"]' }], sides: ["below"],
    title: "See where you stand",
    body: "Paid, open and planned income, and what’s left after tax.",
  },

  // -- The settings ----------------------------------------------------------
  {
    part: 1, node: 0, view: "settings",
    filter: () => ({ tab: "profile" }), via: settingsTab("profile"),
    targets: [{ selector: '[data-tour="settings-profile"]' }], sides: ["right", "below"],
    title: "Your details",
    body: "Your name and contact details go on every invoice.",
  },
  {
    part: 1, node: 1, view: "settings",
    filter: () => ({ tab: "region" }), via: settingsTab("region"),
    targets: [{ selector: '[data-tour="settings-region-tax"]' }], sides: ["below", "right"],
    title: "Where you pay tax",
    body: "Your country sets the tax rates behind your reserves and salary.",
  },
  {
    part: 1, node: 2, view: "settings",
    filter: () => ({ tab: "invoicing" }), via: settingsTab("invoicing"),
    targets: [{ selector: '[data-tour="settings-invoicing"]', each: true }], sides: ["right", "below"],
    title: "How invoices look",
    body: "Template, language and numbering, for every invoice.",
  },
  {
    part: 1, node: 3, view: "settings",
    filter: () => ({ tab: "llm" }), via: settingsTab("llm"),
    targets: [{ selector: '[data-tour="settings-llm"]' }], pulses: ['[data-nav="import"]'], sides: ["below", "right"],
    title: "Connect an AI model",
    body: "A local model or a provider. Then Import fills in forms from your PDFs.",
  },

  {
    kind: "outro", view: "dashboard",
    pulses: ['[data-tour="tour"]'],
    title: "Your turn",
    body: "Start with your first client. Your data stays on this computer.",
  },
];
