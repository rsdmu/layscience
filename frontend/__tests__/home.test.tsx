import { render, screen } from "@testing-library/react";
import Home from "../app/page";

describe("Home", () => {
  it("shows summarizer and registration link", () => {
    render(<Home />);
    expect(
      screen.getByRole("button", { name: /summarize/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /create account/i })
    ).toBeInTheDocument();
  });
});
