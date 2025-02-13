document.addEventListener("DOMContentLoaded", () => {
    let currentPage = 1;
    const limit = 10;
    let currentSearchParams = new URLSearchParams();
    let predictedCuisine = null;

   
    window.getCurrentLocation = () => {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    document.getElementById('latitude').value = position.coords.latitude;
                    document.getElementById('longitude').value = position.coords.longitude;
                    searchByLocation();
                },
                (error) => {
                    console.error("Error getting location:", error);
                    alert("Error getting your location. Please enter coordinates manually.");
                }
            );
        } else {
            alert("Geolocation is not supported by your browser");
        }
    };


    window.searchByLocation = () => {
        const lat = document.getElementById('latitude').value;
        const lon = document.getElementById('longitude').value;
        const radius = document.getElementById('radius').value || 3;

        if (lat && lon) {
            currentSearchParams = new URLSearchParams({
                latitude: lat,
                longitude: lon,
                radius: radius
            });

            if (predictedCuisine) {
                currentSearchParams.append('cuisine', predictedCuisine);
            }
            
            currentPage = 1;
            fetchRestaurants();
        } else {
            alert("Please enter both latitude and longitude");
        }
    };

    
    window.uploadImage = async () => {
        const fileInput = document.getElementById('imageUpload');
        const file = fileInput.files[0];
        const cuisineResult = document.getElementById('cuisineResult');

        if (!file) {
            alert('Please select an image first');
            return;
        }

        const formData = new FormData();
        formData.append('image', file);

        try {
            cuisineResult.textContent = 'Analyzing image...';
            
            const response = await fetch('http://127.0.0.1:5000/predict-cuisine', {
                method: 'POST',
                body: formData,
                timeout: 30000                 
            });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const data = await response.json();
            predictedCuisine = data.cuisine;
            cuisineResult.textContent = `Detected Cuisine: ${predictedCuisine}`;
        } catch (error) {
            console.error('Error:', error);
            cuisineResult.textContent = 'Error analyzing image';
        }
    };

    
    window.searchByCuisine = () => {
        if (!predictedCuisine) {
            alert('Please detect a cuisine first');
            return;
        }

        
        const lat = document.getElementById('latitude').value;
        const lon = document.getElementById('longitude').value;
        const radius = document.getElementById('radius').value || 3;

        currentSearchParams = new URLSearchParams();
        
        if (lat && lon) {
            currentSearchParams.set('latitude', lat);
            currentSearchParams.set('longitude', lon);
            currentSearchParams.set('radius', radius);
        }

        currentSearchParams.set('cuisine', predictedCuisine);
        currentPage = 1;
        fetchRestaurants();
    };

    function fetchRestaurants() {
        const params = new URLSearchParams(currentSearchParams);
        params.append('page', currentPage);
        params.append('limit', limit);

        fetch(`http://127.0.0.1:5000/restaurants?${params.toString()}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data && Array.isArray(data.restaurants)) {
                    displayRestaurants(data.restaurants);
                    updatePagination(data.total);
                } else {
                    console.error("Invalid API response format:", data);
                    document.getElementById("restaurant-list").innerHTML = 
                        "<div class='restaurant-card'>No restaurants found</div>";
                }
            })
            .catch(error => {
                console.error("Error fetching restaurant list:", error);
                document.getElementById("restaurant-list").innerHTML = 
                    "<div class='restaurant-card'>Error loading restaurants</div>";
            });
    }

  
    function displayRestaurants(restaurants) {
        const restaurantContainer = document.getElementById("restaurant-list");
        restaurantContainer.innerHTML = "";

        if (restaurants.length === 0) {
            restaurantContainer.innerHTML = "<div class='restaurant-card'>No restaurants found in this area</div>";
            return;
        }

        restaurants.forEach(item => {
            const restaurant = item.restaurant || item;
            const location = restaurant.location || {};
            const rating = restaurant.user_rating || {};

            const card = document.createElement("div");
            card.className = "restaurant-card";
            card.onclick = () => {
                if (restaurant.photos_url) {
                    window.open(restaurant.photos_url, '_blank'); 
                } else {
                    alert("Photo URL not available for this restaurant.");
                }
            };

            const ratingColor = rating.rating_color || '666666';
            const distanceText = item.distance ? `<p class="distance">${item.distance} km away</p>` : '';

            card.innerHTML = `
                <div class="restaurant-info">
                    <img class="restaurant-image" 
                         src="${restaurant.thumb || 'placeholder.jpg'}" 
                         alt="${restaurant.name}"
                         onerror="this.src='placeholder.jpg'">
                    <div class="restaurant-details">
                        <h3>${restaurant.name || 'Unnamed Restaurant'}</h3>
                        <p>${location.locality || 'Location not available'}</p>
                        <p>Cuisines: ${restaurant.cuisines || 'Not specified'}</p>
                        <p style="color: #${ratingColor}">Rating: ${rating.aggregate_rating || 'N/A'}</p>
                        <p>Cost for two: ${restaurant.currency || '₹'} ${restaurant.average_cost_for_two || 'N/A'}</p>
                        ${distanceText}
                    </div>
                </div>
            `;

            restaurantContainer.appendChild(card);
        });
    }

    function updatePagination(totalItems) {
        const pageNumber = document.getElementById("page-number");
        const prevBtn = document.getElementById("prev-btn");
        const nextBtn = document.getElementById("next-btn");

        if (!pageNumber || !prevBtn || !nextBtn) {
            console.error("Pagination elements not found!");
            return;
        }

        pageNumber.textContent = `Page ${currentPage}`;
        prevBtn.disabled = currentPage === 1;

        const totalPages = Math.ceil(totalItems / limit);
        nextBtn.disabled = currentPage >= totalPages;
    }

    document.getElementById("next-btn")?.addEventListener("click", () => {
        currentPage++;
        fetchRestaurants();
    });

    document.getElementById("prev-btn")?.addEventListener("click", () => {
        if (currentPage > 1) {
            currentPage--;
            fetchRestaurants();
        }
    });

    fetchRestaurants();
});
