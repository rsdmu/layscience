import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import UserPanel from "@/components/UserPanel";
import { deleteAccount } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  deleteAccount: jest.fn(),
}));

jest.mock("react-hot-toast", () => ({
  __esModule: true,
  default: { success: jest.fn(), error: jest.fn() },
}));

const mockedDeleteAccount = deleteAccount as jest.MockedFunction<typeof deleteAccount>;

describe("UserPanel delete account", () => {
  beforeEach(() => {
    localStorage.setItem("username", "user");
    localStorage.setItem("email", "user@example.com");
    localStorage.setItem("hasAccount", "true");
  });

  afterEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it("calls API and clears localStorage", async () => {
    mockedDeleteAccount.mockResolvedValueOnce({});
    const onClose = jest.fn();
    render(<UserPanel user={{ username: "user", email: "user@example.com" }} onClose={onClose} />);

    fireEvent.click(screen.getByRole("button", { name: /delete my account/i }));

    await waitFor(() => expect(mockedDeleteAccount).toHaveBeenCalled());

    expect(localStorage.getItem("username")).toBeNull();
    expect(localStorage.getItem("email")).toBeNull();
    expect(localStorage.getItem("hasAccount")).toBeNull();
  });
});

