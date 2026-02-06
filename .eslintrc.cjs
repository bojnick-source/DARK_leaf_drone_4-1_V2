module.exports = {
  env: {
    browser: true,
    es2021: true,
  },
  extends: ["eslint:recommended"],
  plugins: ["html"],
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
  },
  ignorePatterns: [
    "build/**",
    "build_on/**",
    "build_off/**",
    "build-ON/**",
    "build-OFF/**",
    "external/**",
    "node_modules/**",
  ],
};
