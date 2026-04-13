const manifestNode = document.querySelector("#manifest");

async function loadManifest() {
  try {
    const response = await fetch("http://127.0.0.1:8080/manifest");
    const payload = await response.json();
    manifestNode.textContent = JSON.stringify(payload, null, 2);
  } catch (error) {
    manifestNode.textContent =
      "API manifest unavailable. Start `python3 -m apps.api.main` to view scaffold metadata.";
  }
}

loadManifest();
