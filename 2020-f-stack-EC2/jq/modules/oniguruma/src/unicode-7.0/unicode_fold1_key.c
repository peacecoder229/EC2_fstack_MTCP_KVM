/* This file was converted by gperf_fold_key_conv.py
      from gperf output file. */
/* ANSI-C code produced by gperf version 3.0.3 */
/* Command-line: /Library/Developer/CommandLineTools/usr/bin/gperf -n -C -T -c -t -j1 -L ANSI-C -F,-1 -N unicode_fold1_key unicode_fold1_key.gperf  */
/* Computed positions: -k'1-3' */



/* This gperf source file was generated by make_unicode_fold_data.py */
#include <string.h>
#include "regenc.h"

#define TOTAL_KEYWORDS 1055
#define MIN_WORD_LENGTH 3
#define MAX_WORD_LENGTH 3
#define MIN_HASH_VALUE 6
#define MAX_HASH_VALUE 1196
/* maximum key range = 1191, duplicates = 0 */

#ifdef __GNUC__
__inline
#else
#ifdef __cplusplus
inline
#endif
#endif
/*ARGSUSED*/
static unsigned int
hash(OnigCodePoint codes[])
{
  static const unsigned short asso_values[] =
    {
         7,    5,    9,   57,    1,   12,  682,  788,  676,  782,
       665,  294,  885,  291,  884,  288,  879,  275,  873,  776,
       659,  772,  379,  745,   45,  272,  871,  266,  865,  157,
         2,   14,  815,  198,  697,  675,   28,  628,  479,  615,
       471,  545,  463,  551,    0,  303,  650,  524,  454,  504,
       648, 1054,  637, 1051,  262, 1045,  450, 1042,  440, 1073,
       864, 1035,  860,  849,  845, 1032,  632,  621,  252,  429,
       242,  614,  232,  838,  221,  835,  210, 1028,  139, 1022,
       127,  832,  115, 1017,   97, 1011,   87,  963,  200,  949,
        77,  178,  190,    0,  417, 1038,  602,  724,  117,  634,
        44, 1055,   60,  331,   27,  816,  168, 1007,  156,  997,
       144, 1001,  408,  387,  396,  991,  280,  763,  272,  981,
       294,  769,  321,  532,  497,  535,  587,  560,  488,  964,
        82,  125,  584,  474,  371,  213,  555,  457,  813,  667,
        64,  448,  810,  508,  990, 1197,  954, 1197,  798,  519,
       793, 1197,  787, 1197,  986, 1197,  188,  431,  374, 1197,
       319,  288,  166, 1197,  763, 1197,   16,    8,  747, 1197,
       981,  397,  945, 1197,  108,  313,  740,  306,  942,  180,
       494,  298,  939,  469,  927,  390,  923,  279,  734,  267,
       920,  257,  727,  234,  721,  304,  917,  264,  914, 1023,
       909,  329,  908, 1014,  181,  555,  869,  212,  623,  202,
       905,  887,  552,  813,  718,  688,  581,  664,  536,  439,
       533,  418,  530,  384,  364,  255,  357,  221,  311,  281,
       349,  229,  339,  143,  520,  114,  513,  268,  710,   63,
       703,   48,  696,  240,  604,   97,  505,  155,  897,  152,
        36,   24,  850,  105,   18,  100,  749,   15,  430
    };
  return asso_values[(unsigned char)onig_codes_byte_at(codes, 2)+3] + asso_values[(unsigned char)onig_codes_byte_at(codes, 1)] + asso_values[(unsigned char)onig_codes_byte_at(codes, 0)];
}

int
unicode_fold1_key(OnigCodePoint codes[])
{
  static const int wordlist[] =
    {
      -1, -1, -1, -1, -1, -1,

      2970,

      2286,

      1013,

      1511,

      1451,

      1490,

      231,

      171,

      210,

      2724,

      559,

      502,

      541,

      1319,

      1259,

      1298,

      1824,

      2376,

      1118,

      1680,

      1250,

      1812,

      387,

      165,

      493,

      2877,

      156,

      1827,

      2304,

      1037,

      1602,

      1499,

      147,

      315,

      219,

      12,

      2811,

      643,

      1244,

      1806,

      1343,

      1307,

      1956,

      1866,

      2658,

      2301,

      1031,

      1595,

      1481,

      2478,

      309,

      201,

      0,

      2805,

      637,

      532,

      120,

      1331,

      1289,

      1944,

      1860,

      2652,

      1034,

      1599,

      2475,

      2337,

      312,

      1656,

      6,

      2808,

      640,

      114,

      1821,

      1337,

      688,

      1950,

      884,

      2655,

      2277,

      1004,

      1580,

      2685,

      881,

      294,

      1076,

      1641,

      2790,

      622,

      2265,

      992,

      1574,

      2835,

      1938,

      288,

      2637,

      1421,

      2784,

      613,

      2259,

      986,

      1571,

      2964,

      1932,

      285,

      2631,

      132,

      2781,

      607,

      159,

      2388,

      1130,

      1692,

      1929,

      153,

      2628,

      3084,

      2253,

      980,

      1568,

      1028,

      1592,

      282,

      102,

      306,

      2778,

      601,

      2802,

      3078,

      2247,

      974,

      1565,

      354,

      2625,

      279,

      2649,

      676,

      2775,

      598,

      1424,

      3072,

      2241,

      968,

      1562,

      2154,

      2622,

      276,

      1046,

      1611,

      2772,

      595,

      324,

      96,

      27,

      2820,

      655,

      875,

      2619,

      1361,

      1043,

      1608,

      144,

      2667,

      321,

      138,

      3183,

      2817,

      652,

      2370,

      1112,

      1355,

      1040,

      1605,

      2148,

      2664,

      318,

      2871,

      18,

      2814,

      2955,

      2280,

      1007,

      1349,

      2433,

      1962,

      1737,

      2661,

      399,

      421,

      2943,

      2361,

      1103,

      2283,

      1010,

      1583,

      375,

      2007,

      297,

      2862,

      2937,

      2793,

      625,

      2271,

      998,

      1577,

      1181,

      2709,

      291,

      2640,

      429,

      2787,

      3066,

      2235,

      962,

      1559,

      1178,

      1935,

      2931,

      2634,

      425,

      2769,

      592,

      3060,

      2229,

      956,

      1556,

      3114,

      1436,

      2616,

      2925,

      77,

      2766,

      589,

      3054,

      2223,

      950,

      1553,

      2019,

      89,

      2613,

      817,

      2919,

      2763,

      3048,

      2217,

      944,

      1550,

      3129,

      1926,

      126,

      2610,

      2130,

      2760,

      3042,

      2211,

      938,

      1547,

      3123,

      1920,

      2142,

      2607,

      833,

      2757,

      3000,

      2169,

      896,

      1526,

      1163,

      1914,

      243,

      2604,

      827,

      2736,

      574,

      2319,

      1058,

      1623,

      108,

      1896,

      336,

      2958,

      52,

      2076,

      1055,

      1620,

      2124,

      1385,

      333,

      1974,

      46,

      83,

      664,

      2961,

      783,

      1379,

      381,

      1968,

      1061,

      1626,

      703,

      3177,

      339,

      2949,

      59,

      2973,

      670,

      2487,

      2565,

      1391,

      3093,

      1980,

      2136,

      2913,

      2469,

      1211,

      1773,

      776,

      2490,

      459,

      2568,

      80,

      2367,

      1109,

      2907,

      1064,

      1629,

      769,

      2022,

      342,

      2868,

      65,

      709,

      1169,

      2583,

      2901,

      1397,

      417,

      1986,

      759,

      706,

      9,

      2133,

      1217,

      1779,

      2895,

      1340,

      465,

      1953,

      92,

      3087,

      2547,

      2472,

      1214,

      1776,

      2889,

      2025,

      462,

      739,

      86,

      2466,

      1208,

      1770,

      2484,

      789,

      456,

      730,

      2463,

      1205,

      1767,

      2145,

      851,

      453,

      724,

      2328,

      3105,

      1647,

      2364,

      1106,

      357,

      2139,

      712,

      2841,

      679,

      1478,

      2865,

      1433,

      198,

      2127,

      807,

      2676,

      529,

      450,

      2712,

      1286,

      2121,

      1854,

      37,

      405,

      857,

      1052,

      1617,

      1370,

      3180,

      330,

      393,

      40,

      2826,

      661,

      854,

      3174,

      1373,

      1049,

      1614,

      2079,

      2118,

      327,

      848,

      34,

      2823,

      2289,

      1016,

      1586,

      1367,

      845,

      300,

      447,

      2670,

      2796,

      628,

      3171,

      3045,

      2214,

      941,

      1256,

      1818,

      2643,

      264,

      499,

      378,

      168,

      586,

      3012,

      2181,

      908,

      1532,

      1917,

      444,

      249,

      2112,

      753,

      2742,

      3006,

      2175,

      902,

      1529,

      2982,

      1908,

      246,

      1517,

      691,

      2739,

      237,

      2562,

      3165,

      2730,

      565,

      1902,

      1508,

      1325,

      2106,

      228,

      1442,

      2040,

      2721,

      556,

      1505,

      402,

      1316,

      225,

      1884,

      2034,

      2718,

      553,

      1502,

      3159,

      1313,

      222,

      1878,

      1430,

      2715,

      550,

      1073,

      1638,

      1310,

      2046,

      1872,

      2397,

      1139,

      1701,

      673,

      1067,

      1632,

      1415,

      2574,

      2004,

      2985,

      71,

      2481,

      1238,

      1800,

      2010,

      1403,

      483,

      1992,

      135,

      366,

      1223,

      1785,

      2850,

      697,

      471,

      2052,

      105,

      1220,

      1782,

      2979,

      369,

      468,

      746,

      99,

      700,

      2892,

      2460,

      1202,

      1764,

      2457,

      1199,

      1761,

      2454,

      1196,

      1758,

      68,

      345,

      2157,

      74,

      2829,

      1400,

      721,

      1989,

      1406,

      2151,

      1995,

      2967,

      736,

      2445,

      1187,

      1749,

      2331,

      1175,

      1650,

      2115,

      1881,

      360,

      2109,

      878,

      2844,

      2103,

      348,

      2016,

      1439,

      2832,

      2556,

      863,

      2679,

      1412,

      3168,

      2001,

      2550,

      3162,

      860,

      2526,

      3156,

      2085,

      2451,

      1193,

      1755,

      2325,

      1079,

      1644,

      842,

      1070,

      1635,

      839,

      2520,

      2838,

      836,

      2514,

      3138,

      1427,

      2508,

      3117,

      1409,

      2673,

      1998,

      2295,

      1022,

      1589,

      1235,

      1797,

      303,
      -1,

      2097,

      2799,

      129,

      821,

      3051,

      2220,

      947,
      -1,

      718,

      2646,

      267,

      3039,

      2208,

      935,

      2439,

      3150,

      1743,

      261,
      -1,

      1923,

      1875,

      583,

      3036,

      2205,

      932,

      1544,

      1911,

      2994,

      2163,

      890,

      1523,

      2754,

      580,

      1869,

      634,

      715,

      1448,

      571,

      2988,

      1941,

      2976,

      1520,

      1890,

      1514,

      240,

      1445,

      234,

      2733,

      568,

      2727,

      562,

      1328,

      1475,

      1322,
      -1,

      195,
      -1,

      3126,

      1460,

      526,

      441,

      180,

      1283,

      363,

      1848,

      511,
      -1,

      685,

      1268,

      1457,

      1842,

      830,

      177,

      2541,
      -1,

      1454,

      508,

      2070,

      174,

      1265,

      1863,

      1836,

      505,

      2100,

      438,

      1262,

      2058,

      1830,

      1232,

      1794,

      1496,
      -1,

      480,

      216,

      123,

      1229,

      1791,

      547,

      3153,

      477,

      1304,

      117,

      1226,

      1788,
      -1,

      2898,

      474,

      2094,

      111,

      2448,

      1190,

      1752,

      2418,

      1160,

      1722,

      2298,

      1025,

      414,

      2415,

      1157,

      1719,

      2055,

      3147,

      411,

      2061,

      2409,

      1151,

      1713,
      -1, -1,

      408,

      2391,

      1133,

      1695,
      -1, -1,

      396,

      2091,

      2379,

      1121,

      1683,

      1253,

      1815,

      390,

      872,

      496,

      2880,

      162,

      2601,

      2067,

      1857,

      869,

      3144,
      -1,

      2373,

      1115,

      1677,

      2598,

      866,

      384,

      2322,

      49,

      2874,

      667,
      -1,

      2595,

      1382,

      62,

      1971,

      786,
      -1, -1,

      1394,

      2589,

      1983,

      780,

      2064,

      1851,

      2355,

      1097,

      1674,

      1845,

      764,

      372,

      2352,

      1094,

      1671,

      1839,

      727,

      2349,

      1091,

      1668,

      2856,

      1833,

      2703,
      -1, -1,

      2853,
      -1, -1,

      2700,

      2340,

      1082,

      1659,

      2334,

      2697,

      1653,

      2307,

      1493,

      435,

      694,

      213,

      2847,

      682,

      15,

      544,

      646,

      2688,

      1301,

      1346,

      2682,

      1959,

      3081,

      2250,

      977,

      3063,

      2232,

      959,

      3057,

      2226,

      953,

      273,

      2088,
      -1,

      270,

      3030,

      2199,

      926,

      1541,

      3027,

      2196,

      923,

      1247,

      1809,

      2751,

      255,

      490,

      3141,

      150,

      577,

      3024,

      2193,

      920,

      1538,

      3018,

      2187,

      914,

      1535,

      1487,

      2748,

      2436,

      207,

      1740,

      2745,

      1484,

      538,

      1472,

      204,

      1295,

      192,
      -1,

      535,

      1469,

      523,

      1292,

      189,

      1280,

      1466,

      1463,

      520,

      186,

      183,

      1277,

      432,

      517,

      514,
      -1,

      1274,

      1271,

      1241,

      1803,
      -1,

      2013,

      487,
      -1,

      141,

      2442,

      1184,

      1746,

      2430,

      2427,

      1734,

      1731,

      3120,
      -1,

      2424,

      2082,

      1728,

      2421,

      2592,

      1725,

      2412,

      1154,

      1716,

      2406,

      1148,

      1710,

      824,

      2403,

      1145,

      1707,

      3135,

      2586,

      2928,
      -1, -1,

      2910,
      -1, -1,

      2904,

      2400,

      1142,

      1704,

      2394,

      1136,

      1698,

      2385,

      1127,

      1689,

      3132,

      2274,

      1001,

      3108,

      3102,

      2886,

      2346,

      1088,

      1665,

      3096,

      619,
      -1,

      3090,

      2037,

      2535,

      2268,

      995,

      811,

      804,

      2049,

      2505,

      351,

      2694,

      797,

      616,
      -1,

      793,
      -1,

      1418,

      773,

      2580,

      2499,

      756,

      2382,

      1124,

      1686,

      749,

      2493,

      2358,

      1100,

      56,

      2883,

      2343,

      1085,

      1662,

      1388,

      2859,

      1977,

      743,

      2313,

      43,

      733,

      2577,

      2316,

      2706,

      1376,

      24,

      1965,

      2691,

      2310,

      31,

      1358,

      658,

      2262,

      989,

      1364,

      21,

      1172,

      649,

      2256,

      983,

      1352,

      610,

      3075,

      2244,

      971,

      1166,
      -1,

      604,

      3069,

      2238,

      965,

      2028,

      3033,

      2202,

      929,

      3021,

      2190,

      917,

      258,

      2292,

      1019,

      252,

      3009,

      2178,

      905,

      3003,

      2172,

      899,

      631,

      2544,

      2952,

      2997,

      2166,

      893,

      2991,

      2160,

      887,

      1905,

      3111,
      -1,

      1899,
      -1, -1,

      3,

      2946,
      -1,

      1893,

      3099,

      1334,

      1887,

      1947,
      -1,

      814,

      3015,

      2184,

      911,

      2538,
      -1, -1, -1,

      2532,

      801,
      -1, -1, -1, -1,

      2502,
      -1, -1, -1, -1, -1,

      2496,
      -1, -1, -1, -1, -1, -1,
      -1, -1, -1, -1, -1, -1,
      -1, -1, -1, -1, -1, -1,
      -1,

      2940,
      -1, -1, -1, -1, -1,

      2934,

      2571,
      -1, -1, -1,

      2922,
      -1, -1, -1, -1, -1,

      2916,
      -1, -1, -1, -1, -1, -1,
      -1, -1, -1, -1, -1, -1,
      -1, -1, -1, -1, -1, -1,
      -1, -1, -1, -1, -1, -1,
      -1, -1, -1, -1, -1, -1,
      -1, -1, -1,

      2073,
      -1, -1, -1, -1, -1,

      2559,
      -1, -1, -1, -1, -1,

      2553,
      -1,

      2529,
      -1, -1,

      2043,
      -1, -1,

      2523,
      -1, -1, -1, -1,

      2517,

      2511,

      2031
    };

  if (0 == 0)
    {
      int key = hash(codes);

      if (key <= MAX_HASH_VALUE)
        {
          int index = wordlist[key];

          if (index >= 0 && onig_codes_cmp(codes, OnigUnicodeFolds1 + index, 1) == 0)
            return index;
        }
    }
  return -1;
}


