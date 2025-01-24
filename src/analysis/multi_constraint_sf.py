import numpy as np
import pandas as pd
from scipy.linalg import lstsq


def calculate_shift_factors_multiple_constraints(mcc_df, shadow_prices_df, tolerance=1e-6):
   """
   Calculate shift factors when multiple constraints are binding simultaneously
  
   Parameters:
   - mcc_df: DataFrame with columns ['Interval', 'Settlement_Location', 'MCC']
   - shadow_prices_df: DataFrame with columns ['Interval', 'Constraint_Name', 'Shadow_Price']
   - tolerance: threshold for considering a shadow price non-zero
  
   Returns: Dictionary of shift factors by interval
   """
   results = {}
  
   # Group by interval to handle each timestamp separately
   for interval, interval_shadow_prices in shadow_prices_df.groupby('Interval'):
       # Get binding constraints (non-zero shadow prices)
       binding = interval_shadow_prices[abs(interval_shadow_prices['Shadow_Price']) > tolerance]
      
       if len(binding) > 0:  # If we have binding constraints
           # Get MCCs for this interval
           interval_mccs = mcc_df[mcc_df['Interval'] == interval]
          
           if len(binding) == 1:
               # Simple case - single binding constraint
               constraint = binding.iloc[0]
               shift_factors = {
                   node: mcc / constraint['Shadow_Price']
                   for node, mcc in zip(interval_mccs['Settlement_Location'],
                                      interval_mccs['MCC'])
               }
              
           else:
               # Multiple binding constraints - use matrix solution
               # Build shadow price matrix (A)
               A = np.diag(binding['Shadow_Price'].values)  # Create diagonal matrix of shadow prices
              
               # Build MCC vector (B) for each node
               shift_factors = {}
               for node in interval_mccs['Settlement_Location'].unique():
                   # Get the MCC value for this node
                   node_mcc = interval_mccs[
                       interval_mccs['Settlement_Location'] == node
                   ]['MCC'].values[0]
                   
                   # Create a vector of the same length as binding constraints
                   node_mcc_vector = np.full(len(binding), node_mcc).reshape(-1, 1)
                   
                   # Solve for shift factors using least squares
                   sf, residuals, rank, s = lstsq(A, node_mcc_vector)
                  
                   # Store results if solution is valid
                   if validate_shift_factors(sf, A, node_mcc_vector):
                       shift_factors[node] = {
                           constraint: sf[i][0]
                           for i, constraint in enumerate(binding['Constraint_Name'])
                       }
          
           results[interval] = {
               'shift_factors': shift_factors,
               'binding_constraints': binding['Constraint_Name'].tolist()
           }
  
   return results


def validate_shift_factors(shift_factors, shadow_prices, mccs, tolerance=1e-6):
   """
   Validate calculated shift factors
   """
   # Check physical bounds
   if not np.all((-1 <= shift_factors) & (shift_factors <= 1)):
       return False
  
   # Check reconstruction error
   reconstructed_mccs = np.dot(shadow_prices, shift_factors)
   if np.any(abs(reconstructed_mccs - mccs) > tolerance):
       return False
  
   return True


def analyze_results(results):
   """
   Analyze and summarize shift factor results
   """
   summary = {}
  
   for interval, data in results.items():
       shift_factors = data['shift_factors']
       constraints = data['binding_constraints']
      
       # Calculate statistics for each constraint
       for constraint in constraints:
           constraint_sfs = [
               sfs[constraint]
               for sfs in shift_factors.values()
               if constraint in sfs
           ]
          
           summary[f"{interval}_{constraint}"] = {
               'mean_sf': np.mean(constraint_sfs),
               'max_sf': np.max(constraint_sfs),
               'min_sf': np.min(constraint_sfs),
               'std_sf': np.std(constraint_sfs)
           }
  
   return pd.DataFrame(summary).T


# Example usage
def main():
   # Sample data
   mcc_data = {
       'Interval': [1, 1, 1, 1],
       'Settlement_Location': ['Node1', 'Node2', 'Node3', 'Node4'],
       'MCC': [10.5, -5.2, 8.7, -3.1]
   }
  
   shadow_prices_data = {
       'Interval': [1, 1, 1],
       'Constraint_Name': ['Constraint1', 'Constraint2', 'Constraint3'],
       'Shadow_Price': [15.0, 8.0, 12.0]
   }
  
   mcc_df = pd.DataFrame(mcc_data)
   shadow_prices_df = pd.DataFrame(shadow_prices_data)
  
   # Calculate shift factors
   results = calculate_shift_factors_multiple_constraints(mcc_df, shadow_prices_df)
  
   # Analyze results
   summary = analyze_results(results)
  
   # Print results
   print("\nShift Factor Summary:")
   print(summary)
  
   # Print detailed results for first interval
   print("\nDetailed Results for Interval 1:")
   for node, sfs in results[1]['shift_factors'].items():
       print(f"\n{node}:")
       for constraint, sf in sfs.items():
           print(f"  {constraint}: {sf:.4f}")


if __name__ == "__main__":
   main()