import React from "react";

export function FooterDefault(){
    return(
  <footer className="footer sm:footer-horizontal footer-center bg-base-300 text-base-content p-4">
  <aside>
    <p>Copyright © {new Date().getFullYear()} - All right reserved by Quantwise</p>
    <p>Made with love  - Hansuja Budhiraja</p>
  </aside>
</footer>
    );
}