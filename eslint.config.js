module.exports = [
  {
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: {
        window: "readonly",
        document: "readonly",
        localStorage: "readonly",
        history: "readonly",
        navigator: "readonly",
        fetch: "readonly",
        XMLHttpRequest: "readonly",
        FormData: "readonly"
      }
    },
    rules: {
      "no-unused-vars": "warn",
      "no-console": "off"
    }
  }
];
