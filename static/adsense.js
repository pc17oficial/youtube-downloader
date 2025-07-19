// Adsense script loader for dynamic pages
function loadAdsense() {
    const script = document.createElement('script');
    script.async = true;
    script.src = "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-3332593525886814";
    script.crossOrigin = "anonymous";
    document.head.appendChild(script);
    setTimeout(() => {
        (adsbygoogle = window.adsbygoogle || []).push({});
    }, 1000);
}
window.addEventListener('DOMContentLoaded', loadAdsense);