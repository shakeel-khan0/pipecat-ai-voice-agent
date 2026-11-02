import { useCallback, useState } from "react";
import { RTVIEvent, TransportState } from "@pipecat-ai/client-js";
import { usePipecatClient, usePipecatClientMicControl, useRTVIClientEvent } from "@pipecat-ai/client-react";

const START_URL = import.meta.env.VITE_PIPECAT_START_URL ?? "/voice/start";

type ConversationState = "disconnected" | "connecting" | "listening" | "processing" | "speaking" | "error";

const STATE_COPY: Record<ConversationState, { label: string; detail: string }> = {
  disconnected: { label: "Ready when you are", detail: "Start a conversation to speak with the AI receptionist." },
  connecting: { label: "Connecting", detail: "Preparing your private voice session…" },
  listening: { label: "Listening", detail: "Go ahead — the receptionist can hear you." },
  processing: { label: "Processing", detail: "Preparing a response…" },
  speaking: { label: "AI speaking", detail: "You can interrupt naturally at any time." },
  error: { label: "Connection issue", detail: "The conversation could not continue." },
};

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  return "The voice connection could not be completed. Please try again.";
}

function MicrophoneIcon({ muted = false }: { muted?: boolean }) {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Z"/><path d="M18 11v1a6 6 0 0 1-10.24 4.24M6 11v1c0 .98.23 1.9.64 2.72M12 18v3M9 21h6"/>{muted && <path d="m4 4 16 16"/>}</svg>;
}

function PhoneIcon({ end = false }: { end?: boolean }) {
  return <svg viewBox="0 0 24 24" aria-hidden="true">{end ? <path d="M4.5 15.5c4.6-3.4 10.4-3.4 15 0l-2.1 3.1-3.2-1.4v-2.1a12 12 0 0 0-4.4 0v2.1l-3.2 1.4-2.1-3.1Z"/> : <path d="M7.2 3.8 10 7.4 8.3 10a14 14 0 0 0 5.7 5.7l2.6-1.7 3.6 2.8-1.5 3.1c-.4.8-1.3 1.2-2.2 1C9.7 19.4 4.6 14.3 3.1 7.5c-.2-.9.2-1.8 1-2.2l3.1-1.5Z"/>}</svg>;
}

export default function App() {
  const client = usePipecatClient();
  const { enableMic, isMicEnabled } = usePipecatClientMicControl();
  const [transportState, setTransportState] = useState<TransportState>("disconnected");
  const [conversationState, setConversationState] = useState<ConversationState>("disconnected");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useRTVIClientEvent(RTVIEvent.TransportStateChanged, useCallback((nextState: TransportState) => {
    setTransportState(nextState);
    if (["initializing", "initialized", "authenticating", "connecting"].includes(nextState)) setConversationState("connecting");
    else if (nextState === "connected" || nextState === "ready") setConversationState("listening");
    else if (nextState === "disconnected") setConversationState("disconnected");
    else if (nextState === "error") setConversationState("error");
  }, []));
  useRTVIClientEvent(RTVIEvent.UserStartedSpeaking, useCallback(() => setConversationState("listening"), []));
  useRTVIClientEvent(RTVIEvent.UserStoppedSpeaking, useCallback(() => setConversationState("processing"), []));
  useRTVIClientEvent(RTVIEvent.BotStartedSpeaking, useCallback(() => setConversationState("speaking"), []));
  useRTVIClientEvent(RTVIEvent.BotStoppedSpeaking, useCallback(() => setConversationState("listening"), []));
  useRTVIClientEvent(RTVIEvent.Error, useCallback((event: unknown) => {
    setError(errorMessage(event));
    setConversationState("error");
  }, []));
  useRTVIClientEvent(RTVIEvent.Disconnected, useCallback(() => {
    setBusy(false);
    setTransportState("disconnected");
    setConversationState("disconnected");
  }, []));

  const connected = transportState === "connected" || transportState === "ready";
  const stateCopy = STATE_COPY[conversationState];

  const startConversation = async () => {
    if (!client) return;
    setBusy(true); setError(""); setConversationState("connecting");
    try { await client.startBotAndConnect({ endpoint: START_URL }); }
    catch (connectionError) { setError(errorMessage(connectionError)); setConversationState("error"); }
    finally { setBusy(false); }
  };

  const endConversation = async () => {
    if (!client) return;
    setBusy(true); setError("");
    try { await client.disconnect(); }
    catch (disconnectError) { setError(errorMessage(disconnectError)); setConversationState("error"); }
    finally { setBusy(false); }
  };

  const toggleMicrophone = async () => {
    setError("");
    try { await enableMic(!isMicEnabled); }
    catch (microphoneError) { setError(errorMessage(microphoneError)); setConversationState("error"); }
  };

  return <main className="app-shell">
    <div className="ambient ambient-one" aria-hidden="true"/><div className="ambient ambient-two" aria-hidden="true"/>
    <header className="site-header">
      <a className="wordmark" href="#main-content" aria-label="AgentiX Labs AI home"><span className="brand-mark" aria-hidden="true">AX</span><span>AgentiX Labs <strong>AI</strong></span></a>
      <span className="demo-label">Voice demo</span>
    </header>

    <section className="demo-layout" id="main-content">
      <div className="intro-panel">
        <p className="eyebrow">AI voice receptionist</p>
        <h1>A natural first conversation for every caller.</h1>
        <p className="lead">Experience the AgentiX Labs AI voice receptionist directly in your browser. Ask a question, explore a business need, or simply see how the conversation flows.</p>
        <div className="feature-note"><span className="privacy-icon" aria-hidden="true">✓</span><p><strong>Private browser session</strong><span>Returning-caller identity is not retained between sessions.</span></p></div>
      </div>

      <section className="voice-card" aria-labelledby="voice-card-title">
        <div className="card-heading"><div><p className="card-kicker">Live conversation</p><h2 id="voice-card-title">Voice Receptionist</h2></div>
          <span className={`connection-pill connection-${conversationState}`}><span aria-hidden="true"/>{connected ? "Connected" : conversationState === "connecting" ? "Connecting" : "Offline"}</span>
        </div>

        <div className={`voice-stage state-${conversationState}`}>
          <div className="orb-wrap" aria-hidden="true"><span className="orb-ring ring-one"/><span className="orb-ring ring-two"/><span className="voice-orb"><span className="voice-bars"><i/><i/><i/><i/><i/></span></span></div>
          <div className="state-copy" role="status" aria-live="polite"><h3>{stateCopy.label}</h3><p>{!isMicEnabled && connected ? "Your microphone is muted." : stateCopy.detail}</p></div>
        </div>

        {error && <div className="error-banner" role="alert"><span aria-hidden="true">!</span><p><strong>Something went wrong</strong>{error}</p></div>}

        <div className="controls" aria-label="Conversation controls">
          {!connected ? <button className="button button-primary button-start" type="button" onClick={startConversation} disabled={busy || conversationState === "connecting"}><PhoneIcon/>{conversationState === "connecting" ? "Connecting…" : "Start conversation"}</button> : <>
            <button className={`button button-secondary ${!isMicEnabled ? "is-muted" : ""}`} type="button" onClick={toggleMicrophone} disabled={busy} aria-pressed={!isMicEnabled}><MicrophoneIcon muted={!isMicEnabled}/>{isMicEnabled ? "Mute" : "Unmute"}</button>
            <button className="button button-danger" type="button" onClick={endConversation} disabled={busy}><PhoneIcon end/>End conversation</button>
          </>}
        </div>
        <p className="permission-note">Your browser will ask for microphone access when you start.</p>
      </section>
    </section>
    <footer><span>AgentiX Labs AI</span><span aria-hidden="true">•</span><span>Browser voice experience</span></footer>
  </main>;
}
