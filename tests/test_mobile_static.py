from pathlib import Path


MOBILE_ROOT = Path("mobile")


def read_mobile_source() -> str:
    source_files = [
        path
        for path in [*MOBILE_ROOT.glob("app/**/*.tsx"), *MOBILE_ROOT.glob("src/**/*.ts"), *MOBILE_ROOT.glob("src/**/*.tsx")]
        if path.is_file()
    ]
    return "\n".join(path.read_text(encoding="utf-8") for path in source_files)


def test_mobile_uses_secure_store_not_async_storage() -> None:
    source = read_mobile_source()

    assert "expo-secure-store" in source
    assert "SecureStore.setItemAsync" in source
    assert "SecureStore.deleteItemAsync" in source
    assert "AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY" in source
    assert "AsyncStorage" not in source


def test_mobile_has_form_validation_and_safe_errors() -> None:
    source = read_mobile_source()

    assert "emailPattern" in source
    assert "Password must be at least 8 characters." in source
    assert "fallbackMessage" in source
    assert "console.log" not in source
    assert "console.error" not in source


def test_mobile_has_protected_navigation_and_logout() -> None:
    source = read_mobile_source()

    assert '<Redirect href="/(auth)/login"' in source
    assert '<Redirect href="/(app)"' in source
    assert "onPress={logout}" in source


def test_mobile_has_recurring_screen_and_detection_cta() -> None:
    source = read_mobile_source()

    assert "Recurring" in source
    assert "Detect recurring payments" in source
    assert "Pattern confidence" in source
    assert "No recurring payments detected yet." in source


def test_mobile_has_budget_leaks_screen_and_neutral_copy() -> None:
    source = read_mobile_source()

    assert "Insights" in source
    assert "For you" in source
    assert "Run detection" in source
    assert "No budget leaks detected yet." in source
    assert "Detected from imported data" in source
    assert "bad spending" not in source.lower()
    assert "overspending" not in source.lower()
    assert "you should cancel" not in source.lower()


def test_mobile_has_phase_8_home_dashboard_contract() -> None:
    source = read_mobile_source()

    assert "Here's your financial pulse." in source
    assert "Based on imported transactions" in source
    assert "Upcoming charges" in source
    assert "Top categories" in source
    assert "Recent transactions" in source
    assert "Spending insights" in source
    assert 'title: "Home"' in source
    assert 'title: "Insights"' in source
    assert 'title: "Add"' in source
    assert 'title: "Recurring"' in source
    assert 'title: "Profile"' in source
    assert "cancel this" not in source.lower()
    assert "stop spending" not in source.lower()


def test_mobile_has_phase_11_dark_theme_and_shared_ui() -> None:
    source = read_mobile_source()

    assert "#050807" in source
    assert "#34d178" in source
    assert "export { Screen }" in source
    assert "ConfirmModal" in source
    assert "No bank connection required" in source
    assert "Spot spending patterns before they become habits." in source
    assert "Upload a CSV file from iOS Files." in source
    assert "Load synthetic transactions to explore Tally." in source
    assert "Full Portfolio Demo" in source
    assert "Subscription Creep" in source
    assert "Budget Leaks" in source
    assert "Needs Review" in source
    assert "Demo data loaded. You can now explore your dashboard." in source
    assert "Synthetic sample data. For portfolio preview only." in source
    assert "/demo/scenarios" in source
    assert "/demo/reset" in source
    assert "reset_existing_demo" in source


def test_mobile_has_monthly_report_screen_and_safe_copy() -> None:
    source = read_mobile_source()

    assert "Monthly Report" in source
    assert "A neutral summary of your imported transactions." in source
    assert "generateMonthlyReport" in source
    assert "getMonthlyReports" in source
    assert "getMonthlyReportById" in source
    assert "Generated from imported data only. Not financial advice." in source
    assert "No report available yet." in source
    assert "Import transactions or try demo data to generate your monthly report." in source
    assert "/reports/monthly/generate" in source
    assert "/reports/monthly" in source
    assert "you should" not in source.lower()
    assert "bad spending" not in source.lower()
    assert "stop spending" not in source.lower()


def test_mobile_has_privacy_settings_controls_and_confirmations() -> None:
    source = read_mobile_source()

    assert "Tally does not connect to your bank." in source
    assert "Your insights are based only on imported/manual/demo transactions." in source
    assert "Export my Tally data" in source
    assert "Clear demo data" in source
    assert "Delete app data" in source
    assert "Delete account" in source
    assert "DELETE MY TALLY DATA" in source
    assert "DELETE MY ACCOUNT" in source
    assert "Confirmation text does not match." in source
    assert "getPrivacySummary" in source
    assert "exportUserData" in source
    assert "clearDemoData" in source
    assert "deleteAppData" in source
    assert "deleteAccount" in source
    assert "/settings/privacy/summary" in source
    assert "/settings/privacy/export" in source
    assert "/settings/privacy/clear-demo-data" in source
    assert "/settings/privacy/delete-app-data" in source
    assert "/settings/privacy/delete-account" in source
    assert "We couldn't delete your data. Please try again." in source
