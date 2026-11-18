import { createContext, useContext, useCallback, useRef } from "react";

export interface NavigationFilter {
  contractId?: number;
  clientId?: number;
  projectId?: number;
  invoiceId?: number;
  /** Settings tab to open, e.g. "llm". */
  tab?: string;
  /** Invoice list filter to start with, e.g. "Overdue". */
  invoiceStatus?: string;
  /** Open the New Invoice dialog, for `projectId` if given. */
  newInvoice?: boolean;
  /** Open the selected client, contract or project in its edit form. */
  edit?: boolean;
  /** Time Tracking day to open, as YYYY-MM-DD. */
  day?: string;
}

interface NavigationContextValue {
  navigate: (view: string, filter?: NavigationFilter) => void;
  filter: NavigationFilter;
}

const NavigationContext = createContext<NavigationContextValue>({
  navigate: () => {},
  filter: {},
});

export function useNavigation() {
  return useContext(NavigationContext);
}

export { NavigationContext };
