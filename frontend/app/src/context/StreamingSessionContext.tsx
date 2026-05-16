import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';

type StreamingSessionContextType = {
  streamingActive: boolean;
  setStreamingActive: (value: boolean) => void;
};

const StreamingSessionContext = createContext<StreamingSessionContextType | null>(null);

export function StreamingSessionProvider({ children }: { children: ReactNode }) {
  const [streamingActive, setStreamingActiveState] = useState(false);
  const setStreamingActive = useCallback((value: boolean) => {
    setStreamingActiveState(value);
  }, []);
  const value = useMemo(
    () => ({ streamingActive, setStreamingActive }),
    [streamingActive, setStreamingActive],
  );
  return (
    <StreamingSessionContext.Provider value={value}>{children}</StreamingSessionContext.Provider>
  );
}

export function useStreamingSession(): StreamingSessionContextType {
  const ctx = useContext(StreamingSessionContext);
  if (!ctx) throw new Error('useStreamingSession must be used within StreamingSessionProvider');
  return ctx;
}
