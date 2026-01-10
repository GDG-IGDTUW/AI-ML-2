import React from "react";

export function NavbarDefault(){
    return(
      <nav className="w-full bg-black shadow-md sticky top-0 z-50 px-6 py-4 flex justify-between items-center">
      <h2 className="text-2xl font-bold text-white">QuantWise</h2>
      <div className="space-x-1">
        <a href="./pages/PricePredictor" className="text-white px-4 py-2">Predict</a>
        <a href="/SipPlaning" className="text-white px-4 py-2">Plan</a>
        <a href="/ChatBot" className="text-white px-4 py-2">FinBuddy</a>
    
      </div>
      <div className="space-x-4">
        <a href="/login" className="text-black bg-amber-50 rounded-2xl px-4 py-2">Login</a>
        <a href="/signup" className="text-black bg-amber-50 rounded-2xl px-4 py-2">Sign Up</a>
      </div>
    </nav>
    );
}