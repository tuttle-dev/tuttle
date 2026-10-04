import { createContext, useContext, useCallback, useRef } from "react";

export interface NavigationFilter {
  contractId?: number;
  clientId?: number;
  projectId?: number;
  invoiceId?: number;
  /** Settings tab to open, e.g. "llm". */
  tab?: string;
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
