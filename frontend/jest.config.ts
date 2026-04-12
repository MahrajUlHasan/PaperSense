import type { Config } from "jest";
import nextJest from "next/jest.js";

const createJestConfig = nextJest({ dir: "./" });

const config: Config = {
  coverageProvider: "v8",
  testEnvironment: "jsdom",
  setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"],
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
  },
  transformIgnorePatterns: [
    "node_modules/(?!(react-markdown|remark-gfm|devlop|micromark|mdast-util|unist|ccount|escape-string-regexp|markdown-table|unified|bail|is-plain-obj|trough|vfile|decode-named-character-reference|character-entities|trim-lines)/)",
  ],
};

export default createJestConfig(config);
