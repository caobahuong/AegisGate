import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { ToastProvider, useToast } from "@/shared/hooks/useToast";

const TestToastConsumer = () => {
  const { showToast, dismissToast } = useToast();
  return (
    <div>
      <button onClick={() => showToast("Success notification", "success")}>Show Success</button>
      <button onClick={() => showToast("Error alert", "error")}>Show Error</button>
      <button onClick={() => showToast("Warning notice", "warning")}>Show Warning</button>
      <button onClick={() => dismissToast("toast-1")}>Dismiss Toast</button>
    </div>
  );
};

describe("Toast System", () => {
  it("renders toasts, supports stacking and manual dismiss", () => {
    render(
      <ToastProvider>
        <TestToastConsumer />
      </ToastProvider>
    );

    // Initial state: no toasts
    expect(screen.queryByText("Success notification")).toBeNull();

    // Trigger success toast
    fireEvent.click(screen.getByText("Show Success"));
    expect(screen.getByText("Success notification")).toBeDefined();
    expect(screen.getByRole("status")).toBeDefined();

    // Trigger error toast (stacking)
    fireEvent.click(screen.getByText("Show Error"));
    expect(screen.getByText("Error alert")).toBeDefined();
    expect(screen.getByRole("alert")).toBeDefined();

    // Both are present
    expect(screen.getByText("Success notification")).toBeDefined();
    expect(screen.getByText("Error alert")).toBeDefined();

    // Click dismiss button on error toast
    const dismissButtons = screen.getAllByRole("button", { name: "Dismiss notification" });
    fireEvent.click(dismissButtons[1]);

    expect(screen.queryByText("Error alert")).toBeNull();
    expect(screen.getByText("Success notification")).toBeDefined();
  });
});
