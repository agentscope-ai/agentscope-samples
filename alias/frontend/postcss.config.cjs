const tailwindcss = require('tailwindcss');
const autoprefixer = require('autoprefixer');
const postcssImport = require('postcss-import');
const postcssNesting = require('postcss-nesting');

module.exports = {
  plugins: [
    postcssImport,
    postcssNesting,
    tailwindcss,
    autoprefixer,
  ]
}