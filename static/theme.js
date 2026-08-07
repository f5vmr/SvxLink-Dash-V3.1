(function () {
    "use strict";

    const storageKey = "svxlink-status-theme";
    const root = document.documentElement;
    const darkPreference = window.matchMedia(
        "(prefers-color-scheme: dark)"
    );

    function getStoredTheme() {
        try {
            const stored = localStorage.getItem(storageKey);

            if (stored === "dark" || stored === "light") {
                return stored;
            }
        } catch (error) {
            // Continue using the browser colour preference.
        }

        return null;
    }

    function getPreferredTheme() {
        return getStoredTheme() ||
            (darkPreference.matches ? "dark" : "light");
    }

    function applyTheme(theme) {
        const dark = theme === "dark";

        root.classList.toggle("dark-mode", dark);
        root.style.colorScheme = dark ? "dark" : "light";

        const button = document.getElementById("theme-toggle");

        if (button) {
            button.textContent = dark ? "☀ Light mode" : "☾ Dark mode";
            button.setAttribute(
                "aria-label",
                dark ? "Use light mode" : "Use dark mode"
            );
            button.setAttribute(
                "title",
                dark ? "Use light mode" : "Use dark mode"
            );
            button.setAttribute("aria-pressed", dark ? "true" : "false");
        }
    }

    /*
     * Apply the theme immediately. Because theme.js is loaded from the
     * document head, this minimises a flash of the light theme.
     */
    applyTheme(getPreferredTheme());

    document.addEventListener("DOMContentLoaded", function () {
        const button = document.createElement("button");

        button.id = "theme-toggle";
        button.className = "theme-toggle";
        button.type = "button";

        button.addEventListener("click", function () {
            const newTheme = root.classList.contains("dark-mode")
                ? "light"
                : "dark";

            try {
                localStorage.setItem(storageKey, newTheme);
            } catch (error) {
                // The theme will still work for the current page.
            }

            applyTheme(newTheme);
        });

        document.body.appendChild(button);
        applyTheme(getPreferredTheme());
    });

    /*
     * Follow an operating-system theme change only when the user has not
     * made an explicit choice for this browser.
     */
    darkPreference.addEventListener("change", function (event) {
        if (!getStoredTheme()) {
            applyTheme(event.matches ? "dark" : "light");
        }
    });
})();