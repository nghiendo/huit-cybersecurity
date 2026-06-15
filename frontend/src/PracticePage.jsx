import { useState } from "react";
import { LayoutPanelLeft, ShieldCheck, TerminalSquare } from "lucide-react";

function PracticePage({ navigate }) {
  const [loginPayload, setLoginPayload] = useState("admin'--");
  const [commentPayload, setCommentPayload] = useState("<script>alert(1)</script>");
  const [loginOutput, setLoginOutput] = useState("login-console> awaiting_input");
  const [commentOutput, setCommentOutput] = useState("comment-console> awaiting_input");
  const [loginLoading, setLoginLoading] = useState(false);
  const [commentLoading, setCommentLoading] = useState(false);

  async function submitLogin(event) {
    event.preventDefault();
    if (!loginPayload.trim() || loginLoading) {
      return;
    }

    setLoginLoading(true);
    try {
      const response = await fetch("/api/lab", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ input: loginPayload })
      });
      if (!response.ok) {
        throw new Error("Request failed");
      }

      const data = await response.json();
      setLoginOutput(
        [
          "login-console> response_received",
          `payload: ${loginPayload}`,
          "",
          JSON.stringify(
            {
              ok: data.ok,
              mode: data.mode,
              sql: data.result?.sql,
              security: data.security,
              endpointTimeMs: data.endpointTimeMs
            },
            null,
            2
          )
        ].join("\n")
      );
    } catch {
      setLoginOutput(
        ["login-console> request_failed", `payload: ${loginPayload}`, "error: network_or_server_failure"].join("\n")
      );
    } finally {
      setLoginLoading(false);
    }
  }

  async function submitComment(event) {
    event.preventDefault();
    if (!commentPayload.trim() || commentLoading) {
      return;
    }

    setCommentLoading(true);
    try {
      const response = await fetch("/api/lab", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ input: commentPayload })
      });
      if (!response.ok) {
        throw new Error("Request failed");
      }

      const data = await response.json();
      setCommentOutput(
        [
          "comment-console> response_received",
          `payload: ${commentPayload}`,
          "",
          JSON.stringify(
            {
              ok: data.ok,
              mode: data.mode,
              xss: data.result?.xss,
              security: data.security,
              endpointTimeMs: data.endpointTimeMs
            },
            null,
            2
          )
        ].join("\n")
      );
    } catch {
      setCommentOutput(
        ["comment-console> request_failed", `payload: ${commentPayload}`, "error: network_or_server_failure"].join("\n")
      );
    } finally {
      setCommentLoading(false);
    }
  }

  return (
    <main className="classic-shell">
      <header className="classic-topbar">
        <div>
          <p className="classic-kicker">Practice Screen</p>
          <h1>Classic login and comment lab</h1>
        </div>
        <div className="classic-actions">
          <button className="admin-button ghost" type="button" onClick={() => navigate("lab")}>
            <LayoutPanelLeft size={18} />
            <span>Lab</span>
          </button>
          <button className="admin-button ghost" type="button" onClick={() => navigate("admin")}>
            <ShieldCheck size={18} />
            <span>Admin</span>
          </button>
        </div>
      </header>

      <section className="classic-grid">
        <article className="classic-panel">
          <div className="classic-head">
            <h2>SQLi Login</h2>
            <p>Classic username and password form for simulated login bypass study.</p>
          </div>
          <form className="classic-form" onSubmit={submitLogin}>
            <label className="classic-label">
              <span>Username</span>
              <input
                className="classic-input"
                onChange={(event) => setLoginPayload(event.target.value)}
                type="text"
                value={loginPayload}
              />
            </label>
            <label className="classic-label">
              <span>Password</span>
              <input className="classic-input" type="password" value="hunter2" readOnly />
            </label>
            <button className="classic-submit" disabled={loginLoading} type="submit">
              {loginLoading ? "Checking..." : "Login"}
            </button>
          </form>
          <div className="classic-console">
            <div className="classic-console-head">
              <TerminalSquare size={16} />
              <span>SQLi console</span>
            </div>
            <pre>{loginOutput}</pre>
          </div>
        </article>

        <article className="classic-panel">
          <div className="classic-head">
            <h2>XSS Comment</h2>
            <p>Classic comment box for simulated stored and reflected script payload study.</p>
          </div>
          <form className="classic-form" onSubmit={submitComment}>
            <label className="classic-label">
              <span>Name</span>
              <input className="classic-input" type="text" value="guest" readOnly />
            </label>
            <label className="classic-label">
              <span>Comment</span>
              <textarea
                className="classic-textarea"
                onChange={(event) => setCommentPayload(event.target.value)}
                rows={7}
                value={commentPayload}
              />
            </label>
            <button className="classic-submit" disabled={commentLoading} type="submit">
              {commentLoading ? "Posting..." : "Post Comment"}
            </button>
          </form>
          <div className="classic-console">
            <div className="classic-console-head">
              <TerminalSquare size={16} />
              <span>XSS console</span>
            </div>
            <pre>{commentOutput}</pre>
          </div>
        </article>
      </section>
    </main>
  );
}

export default PracticePage;
