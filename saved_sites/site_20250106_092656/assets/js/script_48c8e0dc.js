
// Define the MutationObserver callback function
var observerCallback = function(mutationsList, observer) {
  for (var mutation of mutationsList) {
    if (mutation.type === 'childList') {
      var newElements = mutation.addedNodes;
      for (var i = 0; i < newElements.length; i++) {
        if (newElements[i].tagName === "IMG" || newElements[i].tagName === "IFRAME") {
          if (newElements[i].src.indexOf("simpli") !== -1 || newElements[i].src.indexOf("liadm") !== -1 || newElements[i].src.indexOf("onetag") !== -1 || newElements[i].src.indexOf("lijit") !== -1) {
            newElements[i].style.display = "none";
          }
        }
      }
    }
  }
};

// Create a MutationObserver object and observe the body element
var observer = new MutationObserver(observerCallback);
observer.observe(document.body, { childList: true, subtree: true });
