import cgi
import urllib
import urllib2
import webapp2
import datetime
import string

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.api import urlfetch
from django.utils import simplejson
  
import jinja2
import os
jenv = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))
    

class TwitterSearch(db.Model):
  """Search Results Model
  """
  query         = db.StringProperty() 
  hits          = db.IntegerProperty()
  users_average = db.FloatProperty()
  

class IndexHandler(webapp2.RequestHandler):
  """Main Request Handler
  """
  # twitter search url
  searchUrl = "http://search.twitter.com/search.json"
  

  def get(self):
    """Request handler method:
       parse request
       compute and store averages
       render search results page
    """
    message = "" 
    query = ""
    results = dict()
    
    try:
      # parse request 
      query = (self.request.get('q')).lower()
          
      if query:
        # fetch results
        results = self.fetch_results(query)
        
        # update entity for this query
        ts = TwitterSearch.gql("WHERE query = :query", query=query)
        if ts.count() < 1: # we have a new query
          ts = TwitterSearch(query         = query, 
                             hits          = 1, 
                             users_average = self.computeAverages(0.0,results))
          ts.put()
        else: # update current
          for t in ts:
            t.hits += 1
            t.users_average = self.computeAverages(t.users_average, results)
            t.put()
    except Exception as e :
      message = self.handleError(e)
      
    # get stats
    resultsAverages = TwitterSearch.gql("ORDER BY hits DESC LIMIT 10")
        
    template_values = {
      'query'           : query,
      'results'         : results,
      'resultsAverages' : resultsAverages,
      'message'         : message,
    }
        
    template = jenv.get_template('index.html')
    self.response.out.write(template.render(template_values))

    
  def fetch_results(self, q):
    """Fetch results and handle API responses
    """
    params = urllib.urlencode({
                          'q'   : q,
                          'rpp' : 100, # result per page
                          })
                          
    url = self.searchUrl + "?" + params
    results = urlfetch.fetch(url)
    results = simplejson.loads(results.content)

    # handle search api errors
    if 'error' in results:
      raise Exception(results['error'])
      
    if 'results' in results:
      return results['results']
      
    return dict()


  def computeAverages(self, currentAvg, results):
    """Compute averages
    """
    # sum up average number of distinct authors in results
    authors = [r['from_user_id'] for r in results]
    avg = (currentAvg + len(set(authors)))/2.0
    return avg


  def handleError(self, e):
    """Simple error messages handler
    """
    self.error('400')
    return e

    
def set_trace():
    """Debug helper
    """
    import pdb, sys
    debugger = pdb.Pdb(stdin=sys.__stdin__,
        stdout=sys.__stdout__)
    debugger.set_trace(sys._getframe().f_back)
        
app = webapp2.WSGIApplication([('/', IndexHandler)],
                               debug=True)
