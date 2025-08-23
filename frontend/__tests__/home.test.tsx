import { render, screen } from "@testing-library/react";
import Home from "../app/page";

describe("Home", () => {
  it("shows account and test options", () => {
    render(<Home />);
    expect(screen.getByRole("link", { name: /create account/i })).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /test without account/i })
    ).toBeInTheDocument();
  });
});
