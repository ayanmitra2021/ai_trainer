// ESLint configuration — AAH scaffold default (flat config).
//
// Uses @typescript-eslint/parser (already a devDependency) so TypeScript
// syntax does not cause parse errors. Extended from the scaffold skeleton
// to add the TS parser; the rule set is kept minimal — do NOT widen rules
// to silence findings.

import tsParser from "@typescript-eslint/parser";
import tsPlugin from "@typescript-eslint/eslint-plugin";

export default [
  {
    ignores: [
      ".aah/**",
      ".claude/**",
      "node_modules/**",
      "dist/**",
      "build/**",
      "coverage/**",
    ],
  },
  {
    files: ["**/*.{js,mjs,cjs,jsx,ts,tsx}"],
    plugins: {
      "@typescript-eslint": tsPlugin,
    },
    languageOptions: {
      parser: tsParser,
      ecmaVersion: "latest",
      sourceType: "module",
    },
    rules: {
      "no-unused-vars": "off",          // superseded by @typescript-eslint for TS files
      // Conventional: _-prefixed params/vars are intentionally unused (e.g. _event, _totalDomains).
      "@typescript-eslint/no-unused-vars": ["warn", {
        "argsIgnorePattern": "^_",
        "varsIgnorePattern": "^_",
        "ignoreRestSiblings": true,
      }],
      "no-undef": "off",                // TypeScript handles undefined references
    },
  },
];
