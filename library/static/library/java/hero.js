const heroNav = document.querySelector(".hero-nav");

if (heroNav) {
    const toggle = heroNav.querySelector(".hero-menu-toggle");
    const navigation = heroNav.querySelector(".hero-navigation");

    if (toggle && navigation) {
        const mobileScreen = window.matchMedia("(max-width: 1023px)");

        function setMenuOpen(isOpen) {
            heroNav.classList.toggle("is-open", isOpen);

            toggle.setAttribute("aria-expanded", String(isOpen));

            toggle.setAttribute(
                "aria-label",
                isOpen ? "بستن منو" : "باز کردن منو"
            );

            navigation.inert = mobileScreen.matches && !isOpen;
        }

        toggle.hidden = false;
        heroNav.classList.add("menu-ready");
        setMenuOpen(false);

        toggle.addEventListener("click", () => {
            const isOpen = toggle.getAttribute("aria-expanded") === "true";
            setMenuOpen(!isOpen);
        });

        document.addEventListener("keydown", (event) => {
            if (
                event.key === "Escape" &&
                toggle.getAttribute("aria-expanded") === "true"
            ) {
                setMenuOpen(false);
                toggle.focus();
            }
        });

        document.addEventListener("click", (event) => {
            if (!heroNav.contains(event.target)) {
                setMenuOpen(false);
            }
        });

        heroNav.addEventListener("focusout", (event) => {
            if (!heroNav.contains(event.relatedTarget)) {
                setMenuOpen(false);
            }
        });

        navigation.querySelectorAll("a").forEach((link) => {
            link.addEventListener("click", () => {
                setMenuOpen(false);
            });
        });

        mobileScreen.addEventListener("change", () => {
            const focusWasInMenu = navigation.contains(
                document.activeElement
            );

            setMenuOpen(false);

            if (mobileScreen.matches && focusWasInMenu) {
                toggle.focus();
            } else if (
                !mobileScreen.matches &&
                document.activeElement === toggle
            ) {
                navigation.querySelector("a").focus();
            }
        });
    }
}