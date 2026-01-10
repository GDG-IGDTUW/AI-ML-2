import React from "react";
import { WavyBackground } from "@/components/ui/wavy-background";

export function WavyBackgroundDemo() {
  return (
    <WavyBackground className="max-w-4xl mx-auto pb-0 m-0">
      <p className="text-2xl md:text-4xl lg:text-7xl text-white font-bold inter-var text-center">
        Welcome to QuantWise
      </p>
      <p className="text-base md:text-lg mt-4 text-white font-normal inter-var text-center">
        Leverage the power of AI to power your financial decisions
      </p>
    </WavyBackground>
  );
}
