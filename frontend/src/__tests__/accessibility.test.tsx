import React from "react";
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { axe } from "vitest-axe";
import * as matchers from "vitest-axe/matchers";
import type { AxeMatchers } from "vitest-axe/matchers";
import { Header } from "@/components/Header";
import { Sidebar } from "@/components/Sidebar";
import { Button } from "@/shared/ui/Button";
import { Badge } from "@/shared/ui/Badge";
import { Card } from "@/shared/ui/Card";
import { SseIndicator } from "@/shared/ui/SseIndicator";

declare module "vitest" {
  interface Assertion<T = any> {
    toHaveNoViolations(): T;
  }
  interface AsymmetricMatchersContaining {
    toHaveNoViolations(): void;
  }
}

expect.extend(matchers);

describe("Accessibility (axe-core) Checks", () => {
  it("Header has no critical accessibility violations", async () => {
    const { container } = render(
      <Header
        autoMode={false}
        onToggleAutoMode={() => {}}
        mcpOnline={true}
        theme="light"
        onToggleTheme={() => {}}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("Sidebar has no critical accessibility violations", async () => {
    const { container } = render(
      <Sidebar activeTab="monitor" onTabChange={() => {}} plugins={[]} />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("UI Primitives (Button, Badge, Card, SseIndicator) have no violations", async () => {
    const { container } = render(
      <div>
        <Button variant="primary">Submit</Button>
        <Badge variant="success">Completed</Badge>
        <Card title="Test Card">Card content</Card>
        <SseIndicator status="connected" />
      </div>
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
