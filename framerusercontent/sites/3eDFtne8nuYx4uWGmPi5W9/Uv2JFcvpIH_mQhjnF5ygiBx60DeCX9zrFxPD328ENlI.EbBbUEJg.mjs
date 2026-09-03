import React from "./react.B3PFzigR.mjs";

function NotFound() {
  return React.createElement(
    "div",
    {
      style: {
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "sans-serif",
        backgroundColor: "#faf9f7",
        color: "#1a1a1a",
        gap: "16px"
      }
    },
    React.createElement("h1", { style: { fontSize: "32px", margin: 0 } }, "Page Not Found"),
    React.createElement("p", { style: { margin: 0, color: "#666" } }, "The requested page could not be found."),
    React.createElement(
      "a",
      {
        href: "/",
        style: {
          padding: "10px 20px",
          backgroundColor: "#1a1a1a",
          color: "#fff",
          borderRadius: "8px",
          textDecoration: "none",
          fontSize: "14px"
        }
      },
      "Back to Home"
    )
  );
}

export default NotFound;
export const __FramerMetadata__ = { exports: {} };
export const queryParamNames = [];
