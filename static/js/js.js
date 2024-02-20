document.addEventListener('DOMContentLoaded', () => {
  const heroSearchForm = document.getElementById('hero-stock-search-form');
  if (heroSearchForm) {
      heroSearchForm.addEventListener('submit', heroPerformSearch);
  }
});

function showHeroSuggestions(query) {
  const dropdownContent = document.getElementById('hero-dropdown-content');
  if (query.length < 2) {
      dropdownContent.innerHTML = '';
      return;
  }

  fetch(`/search_stocks?q=${query}`)
      .then(response => response.json())
      .then(data => {
          let resultsHTML = '';
          data.forEach(symbol => {
              resultsHTML += `<div class="suggestion-item" onclick="selectStock('${symbol}')">${symbol}</div>`;
          });
          dropdownContent.innerHTML = resultsHTML;
      })
      .catch(error => console.error('Error fetching suggestions:', error));
}

function selectStock(symbol) {
  document.getElementById('hero-stock-search').value = symbol;
  document.getElementById('hero-dropdown-content').innerHTML = '';
  heroPerformSearch(new Event('submit'));
}

function heroPerformSearch(event) {
  event.preventDefault();
  const query = document.getElementById('hero-stock-search').value.trim().toUpperCase();
  fetch(`/stock_details/${query}`)
      .then(response => {
          if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
          return response.json();
      })
      .then(data => {
          if (data.error || data.length === 0) {
              throw new Error('Stock details not found');
          }
          displayStockDetails(data, 'hero-stock-details');
      })
      .catch(error => {
        console.error('Error:', error);
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message'; // Apply the error message class
        errorDiv.textContent = 'Error fetching stock details.';
        document.getElementById('hero-stock-details').innerHTML = ''; // Clear any existing content
        document.getElementById('hero-stock-details').appendChild(errorDiv);
        document.getElementById('hero-stock-details').style.display = 'block';
      });

}

function displayStockDetails(data, elementId) {
  const detailsContainer = document.getElementById(elementId);
  const stock = data[0] ? data[0] : {};

  const content = `
      <h3>${stock.Headline || 'N/A'}</h3>
      <p>${stock.Summary || 'N/A'}</p>
      <p><strong>Price Day Before:</strong> ${stock.News_Day_Before || 'N/A'}</p>
      <p><strong>Price Day Of:</strong> ${stock.News_day || 'N/A'}</p>
      <p><strong>Date:</strong> ${stock.Date ? new Date(stock.Date).toLocaleDateString() : 'N/A'}</p>
      <p><strong>Time:</strong> ${stock.Date_Time ? new Date(stock.Date_Time).toLocaleTimeString() : 'N/A'}</p>
      <p><strong>SMA 10:</strong> ${stock.SMA_10 || 'N/A'}</p>
      <p><strong>SMA 20:</strong> ${stock.SMA_20 || 'N/A'}</p>
      <p><strong>SMA 50:</strong> ${stock.SMA_50 || 'N/A'}</p>
      <p><strong>RSI:</strong> ${stock.RSI || 'N/A'} (${stock.RSI_Analysis || 'N/A'})</p>
      <p><strong>MACD:</strong> ${stock.MACD || 'N/A'} (${stock.MACD_Analysis || 'N/A'})</p>
      <p><strong>MACD Signal:</strong> ${stock.MACD_Signal || 'N/A'}</p>
      <p><strong>Sentiment:</strong> ${stock.Sentiment || 'N/A'}</p>
      <p><strong>Adjusted Sentiment:</strong> ${stock.Adjusted_Sentiment || 'N/A'}</p>
  `;

  detailsContainer.innerHTML = content;
  detailsContainer.style.display = 'block';
}


document.getElementById("runScriptBtn").addEventListener("click", function() {
  document.getElementById("dataDisplay").innerHTML = "Loading... Please wait.";

  fetch('/run-script', { cache: 'no-cache' })
  .then(response => {
      if (!response.ok) {
          throw new Error(`Network response was not ok, status: ${response.status}`);
      }
      return response.json();
  })
  .then(data => {
      console.log(data); // Debugging: Log the data to inspect its structure
      document.getElementById("dataDisplay").innerHTML = "<pre>" + JSON.stringify(data, null, 2) + "</pre>";
      alert("News feed updated successfully.");
  })
  .catch(error => {
    console.error('Error:', error);
    document.getElementById("dataDisplay").innerHTML = `Error loading data. Please try again. Details: ${error}`;
});
});


document.querySelector('select[name="news_symbol"]').addEventListener('change', function() {
    this.style.transform = "scale(11)";
    setTimeout(() => {
      this.style.transform = "scale(10)";
    }, 10);
  });


