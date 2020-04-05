/*
Plugin is taken here: https://github.com//adam-p/markdown-it-headinganchor
Modified to be used in web 1.0
*/
'use strict';
function slugify(md, s) {
  var spaceRegex = new RegExp(md.utils.lib.ucmicro.Z.source, 'g');
  return encodeURIComponent(s.replace(spaceRegex, ''));
}
function makeRule(md, options) {
  return function addHeadingAnchors(state) {
    for (var i = 0; i < state.tokens.length-1; i++) {
      if (state.tokens[i].type !== 'heading_open' ||
          state.tokens[i+1].type !== 'inline') {
        continue;
      }
      var headingOpenToken = state.tokens[i+1];
      var headingInlineToken = state.tokens[i+1];
      if (!headingInlineToken.content) {
        continue;
      }
      var anchorName = slugify(md, headingInlineToken.content);
      if (options.addHeadingID) {
        state.tokens[i].attrPush(['id', anchorName]);
      }
      if (options.addHeadingAnchor) {
        var anchorToken = new state.Token('html_inline', '', 0);
        anchorToken.content =
          '<a name="' +
          anchorName +
          '" class="' +
          options.anchorClass +
          '" href="#"></a>';
        headingInlineToken.children.unshift(anchorToken);
      }
      i += 2;
    }
  };
}
function headinganchor_plugin(md, opts) {
  var defaults = {
    anchorClass: 'markdown-it-headinganchor',
    addHeadingID: true,
    addHeadingAnchor: true
  };
  var options = md.utils.assign(defaults, opts);
  md.core.ruler.push('heading_anchors', makeRule(md, options));
};

