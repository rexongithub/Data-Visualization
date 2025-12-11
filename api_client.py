"""
API client for similarity service
"""
import requests
import pandas as pd
from config import SIMILARITY_API_URL, TOP_N_RESULTS, API_TIMEOUT


class SimilarityAPIClient:
    """Client for interacting with the similarity API"""

    def __init__(self, api_url=SIMILARITY_API_URL):
        self.api_url = api_url

    def check_health(self):
        """
        Check if similarity API is running

        Returns:
            bool: True if API is accessible, False otherwise
        """
        try:
            response = requests.get(f"{self.api_url}/", timeout=2)
            return response.status_code == 200
        except:
            return False

    def get_similar_products(self, product_id, weights, top_n=TOP_N_RESULTS):
        """
        Get similar products from API

        Args:
            product_id: ID of the product to find similarities for
            weights: Dictionary with keys 'text', 'nutrition', 'brand', 'barcode'
            top_n: Number of similar products to return

        Returns:
            tuple: (success: bool, result: DataFrame or error message)
        """
        try:
            # Check API health first
            if not self.check_health():
                error_df = pd.DataFrame({
                    "Error": ["Similarity API is not running. Please start the API server."]
                })
                return False, error_df

            # Prepare request payload
            payload = {
                "product_id": product_id,
                "top_n": top_n,
                "weights": weights
            }

            # Make API request
            response = requests.post(
                f"{self.api_url}/similar",
                json=payload,
                timeout=API_TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()

                # Convert API response to DataFrame
                similar_prods = data['similar_products']
                result_df = pd.DataFrame([
                    {
                        'Rank': p['rank'],
                        'Name': p['name'],
                        'Brand': p['brand'],
                        'Barcode': p.get('barcode', 'N/A'),
                        'Active': 'Yes' if p.get('active', 0) == 1 else 'No',
                        'Score': f"{p['similarity_score']:.4f}",
                        'Energy': p['nutrition']['energy'],
                        'Protein': p['nutrition']['protein'],
                        'Fat': p['nutrition']['fat']
                    }
                    for p in similar_prods
                ])

                # Store the IDs separately for later use
                result_df['_id'] = [p['id'] for p in similar_prods]

                print(
                    f"✅ Found {len(result_df)} similar products for ID {product_id}")
                print(f"   Computation time: {data['computation_time_ms']} ms")

                return True, result_df
            else:
                error_msg = response.json().get('error', 'Unknown error')
                error_df = pd.DataFrame({
                    "Error": [f"API returned error: {error_msg}"]
                })
                print(f"❌ API error: {response.status_code}")
                return False, error_df

        except Exception as e:
            print(f"❌ Error computing similarity: {str(e)}")
            import traceback
            traceback.print_exc()

            error_df = pd.DataFrame({
                "Error": [f"Error: {str(e)}"]
            })
            return False, error_df
