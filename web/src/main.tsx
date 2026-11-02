import React from "react";
import ReactDOM from "react-dom/client";
import { PipecatClient } from "@pipecat-ai/client-js";
import {
  PipecatClientAudio,
  PipecatClientProvider,
} from "@pipecat-ai/client-react";
import {
  SmallWebRTCTransport,
  WavMediaManager,
} from "@pipecat-ai/small-webrtc-transport";

import App from "./App";
import "./styles.css";

const client = new PipecatClient({
  transport: new SmallWebRTCTransport({ mediaManager: new WavMediaManager() }),
  enableMic: true,
  enableCam: false,
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <PipecatClientProvider client={client}>
      <App />
      <PipecatClientAudio />
    </PipecatClientProvider>
  </React.StrictMode>,
);
