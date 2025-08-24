import { render, screen, waitFor } from "@testing-library/react";
import AboutHomeLink from "@/components/AboutHomeLink";
import { usePathname } from "next/navigation";

jest.mock("next/navigation", () => ({
  usePathname: jest.fn(),
}));

const mockedUsePathname = usePathname as jest.Mock;

describe("AboutHomeLink", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("links to about from summarize page", () => {
    mockedUsePathname.mockReturnValue("/summarize");
    render(<AboutHomeLink />);
    const link = screen.getByRole("link", { name: /about/i });
    expect(link).toHaveAttribute("href", "/about");
  });

  it("links home to summarize when account exists", async () => {
    mockedUsePathname.mockReturnValue("/about");
    localStorage.setItem("hasAccount", "true");
    render(<AboutHomeLink />);
    await waitFor(() => {
      const link = screen.getByRole("link", { name: /home/i });
      expect(link).toHaveAttribute("href", "/summarize");
    });
  });

  it("links home to landing when no account", async () => {
    mockedUsePathname.mockReturnValue("/about");
    render(<AboutHomeLink />);
    await waitFor(() => {
      const link = screen.getByRole("link", { name: /home/i });
      expect(link).toHaveAttribute("href", "/");
    });
  });
});
