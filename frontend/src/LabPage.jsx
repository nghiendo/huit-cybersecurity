import { useState } from "react";
import { CornerDownLeft, LayoutPanelLeft, MonitorUp } from "lucide-react";
import { payloadGroups } from "./payloads";

const floatingPayloads = [
  { id: "p1", text: payloadGroups[0].items[0], tone: "tone-sqli-basic", x: "8%", y: "14%", duration: "8.8s", delay: "-1.4s", tilt: "-2deg" },
  { id: "p2", text: payloadGroups[0].items[1], tone: "tone-sqli-basic", x: "78%", y: "16%", duration: "7.9s", delay: "-4.8s", tilt: "1.6deg" },
  { id: "p3", text: payloadGroups[1].items[0], tone: "tone-sqli-advanced", x: "10%", y: "72%", duration: "9.6s", delay: "-2.5s", tilt: "-1.4deg" },
  { id: "p4", text: payloadGroups[1].items[2], tone: "tone-sqli-advanced", x: "70%", y: "70%", duration: "8.2s", delay: "-5.2s", tilt: "2deg" },
  { id: "p5", text: payloadGroups[2].items[0], tone: "tone-xss-basic", x: "6%", y: "42%", duration: "7.4s", delay: "-3.6s", tilt: "-1.8deg" },
  { id: "p6", text: payloadGroups[2].items[1], tone: "tone-xss-basic", x: "77%", y: "40%", duration: "9.1s", delay: "-6.1s", tilt: "1.3deg" },
  { id: "p7", text: payloadGroups[3].items[0], tone: "tone-xss-advanced", x: "21%", y: "86%", duration: "8.6s", delay: "-2.1s", tilt: "-1.2deg" },
  { id: "p8", text: payloadGroups[3].items[1], tone: "tone-xss-advanced", x: "58%", y: "10%", duration: "10.2s", delay: "-7.3s", tilt: "2.1deg" }
];

function LabPage({ navigate }) {
  const [input, setInput] = useState("");
  const [status, setStatus] = useState("idle");
  const [consoleOutput, setConsoleOutput] = useState("console> awaiting_input");

  async function submitPayload(event) {
    event?.preventDefault();
    if (!input.trim() || status === "loading") {
      return;
    }

    setStatus("loading");

    try {
      const response = await fetch("/api/lab", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ input })
      });

      if (!response.ok) {
        throw new Error("Request failed");
      }

      const data = await response.json();
      setConsoleOutput(buildConsoleOutput(data, input));
      setStatus("success");
    } catch {
      setConsoleOutput(
        [
          "console> request_failed",
          "route: /api/lab",
          `payload: ${input}`,
          "error: network_or_server_failure"
        ].join("\n")
      );
      setStatus("error");
    }
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      submitPayload(event);
    }
  }

  return (
    <main className="shell">
      <div className="route-stack">
        <button className="route-button" type="button" onClick={() => navigate("practice")}>
          <MonitorUp size={18} />
          <span>Practice</span>
        </button>
        <button className="route-button" type="button" onClick={() => navigate("admin")}>
          <LayoutPanelLeft size={18} />
          <span>Admin</span>
        </button>
      </div>
      <div className="ambient ambient-a" />
      <div className="ambient ambient-b" />
      {floatingPayloads.map((payload) => (
        <button
          key={payload.id}
          type="button"
          className={`floating-card ${payload.tone}`}
          onClick={() => setInput(payload.text)}
          style={{
            left: payload.x,
            top: payload.y,
            animationDuration: payload.duration,
            animationDelay: payload.delay,
            "--base-tilt": payload.tilt
          }}
        >
          {payload.text}
        </button>
      ))}
      <form className="input-shell" onSubmit={submitPayload}>
        <div className="input-row">
          <textarea
            aria-label="Payload input"
            className={`hero-input is-${status}`}
            onChange={(event) => {
              setInput(event.target.value);
              if (status !== "idle") {
                setStatus("idle");
              }
            }}
            onKeyDown={handleKeyDown}
            placeholder="Type payload and press Enter"
            rows={5}
            spellCheck="false"
            value={input}
          />
          <button
            aria-label="Submit payload"
            className={`enter-button is-${status}`}
            disabled={status === "loading"}
            type="submit"
          >
            <CornerDownLeft size={24} />
          </button>
        </div>
      </form>
      <section className="console-screen" aria-label="Lab console output">
        <pre className="console-output">{consoleOutput}</pre>
      </section>
    </main>
  );
}

function buildConsoleOutput(data, input) {
  const responseSnapshot = {
    ok: data.ok,
    mode: data.mode,
    result: data.result
      ? {
          ...data.result,
          comments: undefined
        }
      : null,
    security: data.security,
    stats: data.stats,
    endpointTimeMs: data.endpointTimeMs
  };

  return [
    "console> response_received",
    "route: /api/lab",
    `payload: ${input}`,
    `timestamp: ${new Date().toISOString()}`,
    "",
    JSON.stringify(responseSnapshot, null, 2)
  ].join("\n");
}

export default LabPage;
