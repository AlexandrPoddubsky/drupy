#!/usr/bin/env python
# $Id: cache.inc,v 1.20 2008/07/02 20:42:25 dries Exp $

"""
  Cache functions

  @package includes
  @see <a href='http://drupy.net'>Drupy Homepage</a>
  @see <a href='http://drupal.org'>Drupal Homepage</a>
  @note Drupy is a port of the Drupal project.
  @note This file was ported from Drupal's includes/cache.inc
  @author Brendon Crawford
  @copyright 2008 Brendon Crawford
  @contact message144 at users dot sourceforge dot net
  @created 2008-01-10
  @version 0.1
  @note License:

    This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 2
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to:
    
    The Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor,
    Boston, MA  02110-1301,
    USA
"""

__version__ = "$Revision: 1 $"

from lib.drupy import DrupyPHP as php
import bootstrap as lib_bootstrap
import database as lib_database

def get(cid, table = 'cache'):
  """
   Return data from the persistent cache. Data may be stored as either plain 
   text or as serialized data. cache_get will automatically return 
   unserialized objects and arrays.
  
   @param cid
     The cache ID of the data to retrieve.
   @param table
     The table table to store the data in.
     Valid core values are 'cache_filter',
     'cache_menu', 'cache_page', or 'cache' for the default cache.
   @return The cache or FALSE on failure.
  """
  # Garbage collection necessary when enforcing a minimum cache lifetime
  cache_flush = lib_bootstrap.variable_get('cache_flush', 0);
  if (cache_flush and (cache_flush + \
      variable_get('cache_lifetime', 0) <= REQUEST_TIME)):
    # Reset the variable immediately to prevent a meltdown in heavy
    # load situations.
    variable_set('cache_flush', 0);
    # Time to php.flush old cache data
    lib_database.query(\
      "DELETE FROM {" + table + "} WHERE expire != %d AND expire <= %d", \
      CACHE_PERMANENT, cache_flush);
  cache = lib_database.fetch_object(lib_database.query(\
    "SELECT data, created, headers, expire, serialized " + \
    "FROM {" + table + "} WHERE cid = '%s'", cid));
  if (php.isset(cache, 'data')):
    # If the data is permanent or we're not enforcing a minimum cache lifetime
    # always return the cached data.
    if (cache.expire == CACHE_PERMANENT or not \
        variable_get('cache_lifetime', 0)):
      if (cache.serialized):
        cache.data = php.unserialize(cache.data);
    # If enforcing a minimum cache lifetime, validate that the data is
    # currently valid for this user before we return it by making sure the
    # cache entry was created before the timestamp in the current session's
    # cache timer. The cache variable is loaded into the user object by
    # _sess_read() in session.inc.
    else:
      if (lib_appglobals.user.cache > cache.created):
        # This cache data is too old and thus not valid for us, ignore it.
        return False;
      else:
        if (cache.serialized):
          cache.data = php.unserialize(cache.data);
    return cache;
  return False;



def set(cid, data, table = 'cache', expire = None, headers = None):
  """
   Store data in the persistent cache.
  
   The persistent cache is split up into four database
   tables. Contributed plugins can add additional tables.
  
   'cache_page': This table stores generated pages for anonymous
   users. This is the only table affected by the page cache setting on
   the administrator panel.
  
   'cache_menu': Stores the cachable part of the users' menus.
  
   'cache_filter': Stores filtered pieces of content. This table is
   periodically cleared of stale entries by cron.
  
   'cache': Generic cache storage table.
  
   The reasons for having several tables are as follows:
  
   - smaller tables allow for faster selects and inserts
   - we try to put fast changing cache items and rather static
     ones into different tables. The effect is that only the fast
     changing tables will need a lot of writes to disk. The more
     static tables will also be better cachable with MySQL's query cache
  
   @param cid
     The cache ID of the data to store.
   @param data
     The data to store in the cache. Complex data types will be
     automatically serialized before insertion.
     Strings will be stored as plain text and not serialized.
   @param table
     The table table to store the data in. Valid core values are 'cache_filter',
     'cache_menu', 'cache_page', or 'cache'.
   @param expire
     One of the following values:
     - CACHE_PERMANENT: Indicates that the item should never be removed unless
       explicitly told to using cache_clear_all() with a cache ID.
     - CACHE_TEMPORARY: Indicates that the item should be removed at the next
       general cache wipe.
     - A Unix timestamp: Indicates that the item should be kept at least until
       the given time, after which it behaves like CACHE_TEMPORARY.
   @param headers
     A string containing HTTP php.header information for cached pages.
  """
  if expire is None:
    expire = lib_bootstrap.CACHE_PERMANENT
    fields = {
      'serialized' : 0,
      'created' : REQUEST_TIME,
      'expire' : expire,
      'headers' : headers
    }
  if (not php.is_string(data)):
    fields['data'] = php.serialize(data)
    fields['serialized'] = 1
  else:
    fields['data'] = data
    fields['serialized'] = 0
  lib_database.merge(table).key({'cid' : cid}).fields(fields).execute()




def clear_all(cid = None, table = None, wildcard = False):
  """
   Expire data from the cache. If called without arguments, expirable
   entries will be cleared from the cache_page and cache_block tables.
  
   @param cid
     If set, the cache ID to delete. Otherwise, all cache entries that can
     expire are deleted.
  
   @param table
     If set, the table table to delete from. Mandatory
     argument if cid is set.
  
   @param wildcard
     If set to TRUE, the cid is treated as a substring
     to match rather than a complete ID. The match is a right hand
     match. If '*' is given as cid, the table table will be emptied.
  """
  if (cid == None and table == None):
    # Clear the block cache first, so stale data will
    # not end up in the page cache.
    clear_all(None, 'cache_block');
    clear_all(None, 'cache_page');
    return;
  if (cid == None):
    if (variable_get('cache_lifetime', 0)):
      # We store the time in the current user's user.cache variable which
      # will be saved into the sessions table by sess_write(). We then
      # simulate that the cache was flushed for this user by not returning
      # cached data that was cached before the timestamp.
      lib_appglobals.user.cache = REQUEST_TIME;
      cache_flush = variable_get('cache_flush', 0);
      if (cache_flush == 0):
        # This is the first request to clear the cache, start a timer.
        variable_set('cache_flush', REQUEST_TIME);
      elif (REQUEST_TIME > (cache_flush + variable_get('cache_lifetime', 0))):
        # Clear the cache for everyone, cache_flush_delay seconds have
        # passed since the first request to clear the cache.
        db_query(\
          "DELETE FROM {" + table + "} WHERE expire != %d AND expire < %d", \
          CACHE_PERMANENT, REQUEST_TIME);
        variable_set('cache_flush', 0);
    else:
      # No minimum cache lifetime, php.flush all temporary cache entries now.
      db_query(\
        "DELETE FROM {" + table + "} WHERE expire != %d AND expire < %d", \
        CACHE_PERMANENT, REQUEST_TIME);
  else:
    if (wildcard):
      if (cid == '*'):
        lib_database.delete(table).execute()
      else:
        lib_database.delete(table).condition('cid', cid +'%', 'LIKE').execute()
    else:
      lib_database.delete(table).condition('cid', cid).execute()



